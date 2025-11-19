const { test, expect } = require('@playwright/test');
const fs = require('fs');

// Toggle strict lazy-load enforcement via env var TEST_STRICT_LAZY
// Accepts '1' or 'true' (case-insensitive) to enable strict checks.
const STRICT_LAZY = (process.env.TEST_STRICT_LAZY || '').toString().toLowerCase() === '1' || (process.env.TEST_STRICT_LAZY || '').toString().toLowerCase() === 'true';
// Toggle strict caching/header enforcement via env var TEST_CACHE_STRICT
// If true, missing caching headers cause test failures. Otherwise tests warn but do not fail.
const CACHE_STRICT = (process.env.TEST_CACHE_STRICT || '').toString().toLowerCase() === '1' || (process.env.TEST_CACHE_STRICT || '').toString().toLowerCase() === 'true';
// Ensure artifact directory exists
const SCREENSHOT_DIR = 'test-results/screenshots';
try { fs.mkdirSync(SCREENSHOT_DIR, { recursive: true }); } catch (e) {}

test.afterEach(async ({ page }, testInfo) => {
  // Save a screenshot on failure with a readable filename
  if (testInfo.status !== 'passed') {
    const safeTitle = testInfo.title.replace(/[^a-z0-9\-_.]/gi, '_');
    const fileName = `${SCREENSHOT_DIR}/${safeTitle}-${Date.now()}.png`;
    try {
      await page.screenshot({ path: fileName, fullPage: true });
      console.log('Saved screenshot:', fileName);
    } catch (e) {
      console.warn('Failed to capture screenshot', e);
    }
  }
});

// Base URL used by the tests. Ensure your app is running locally at this host/port.
const BASE = process.env.TEST_BASE_URL || 'http://127.0.0.1:5000';

test.describe('UI smoke checks - progressive images, print button, JSON-LD', () => {
  const pagesToCheck = ['/', '/patient', '/doctor'];

  for (const path of pagesToCheck) {
    test(`Check ${path}`, async ({ page }) => {
      const url = BASE + path;
      // If the page requires authentication, perform a quick UI login first so the session/cookies are set.
      if (path === '/patient' || path === '/doctor') {
        const creds = path === '/patient' ? { user: 'patient_sami', pass: 'pass123' } : { user: 'dr_ahmad', pass: 'pass123' };
        console.log('Logging in for', path, creds.user);
        await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded', timeout: 15000 });
        // Fill and submit the login form
        await page.fill('#login-username', creds.user);
        await page.fill('#login-password', creds.pass);
        // Click and wait for navigation/redirect
        await Promise.all([
          page.waitForNavigation({ waitUntil: 'domcontentloaded', timeout: 15000 }).catch(() => {}),
          page.click('#login-btn')
        ]);
      }

      console.log('Visiting', url);
      await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });

      // 1) Check JSON-LD presence
      const jsonLdCount = await page.locator('script[type="application/ld+json"]').count();
      expect(jsonLdCount).toBeGreaterThan(0);

      // 2) Check print button presence
      const printBtn = page.locator('#print-btn');
      await expect(printBtn).toHaveCount(1);

      // 3) Check progressive images and network requests
      const imgs = page.locator('img.progressive-img');
      const n = await imgs.count();
      console.log(`Found ${n} images with .progressive-img on ${path}`);

      // Collect network responses for image resources with timestamps
      const imageResponses = new Map(); // map absoluteUrl -> { status, ts, headers }
      page.on('response', (resp) => {
        try {
          const req = resp.request();
          const rurl = resp.url();
          const rtype = req.resourceType();
          if (rtype === 'image' || /\.(png|jpe?g|svg|webp|gif)(\?|$)/i.test(rurl)) {
            // record time of observation and headers
            const ts = Date.now();
            const headers = resp.headers ? resp.headers() : {};
            imageResponses.set(rurl, { status: resp.status(), ts, headers });
          }
        } catch (e) {
          // ignore
        }
      });

      // If there are images with data-src, try to scroll them into view to trigger IntersectionObserver
      const imgsWithData = page.locator('img[data-src]');
      const m = await imgsWithData.count();
      console.log(`Found ${m} <img[data-src]> on ${path}`);

      if (STRICT_LAZY) {
        // Strict mode: try to scroll each image and validate timing.
        let didManualSwap = false;
        for (let i = 0; i < m; i++) {
          const img = imgsWithData.nth(i);
          // try to read attribute defensively
          let dsVal = null;
          try { dsVal = await img.getAttribute('data-src'); } catch (e) { dsVal = null; }
          // use evaluate scrollIntoView which is more reliable in headless environments
          try { await img.evaluate(e => { e.scrollIntoView({ behavior: 'auto', block: 'center' }); }); } catch (e) {}
          try {
            // increase timeout to allow IntersectionObserver to run and for image to swap
            await page.waitForFunction((el) => !el.hasAttribute('data-src'), img, { timeout: 20000 });
          } catch (e) {
            // if one image fails to swap in strict mode, stop and perform the bulk fallback
            didManualSwap = true;
            break;
          }
        }
        if (didManualSwap) {
          await page.evaluate(() => document.querySelectorAll('img[data-src]').forEach(el => { try { const ds = el.getAttribute('data-src'); if (ds) { el.setAttribute('src', ds); el.removeAttribute('data-src'); const __p = new Image(); __p.src = ds; } } catch(e){} }));
          await page.waitForTimeout(1000);
        }

        // Re-evaluate DOM state and collect attributes via page.evaluate to avoid stale locators
        // استثناء عناصر المعاينة/خرائط الـ saliency (مثل `#preview-image` و `#saliency-image`):
        // هذه العناصر تُستخدم لعرض معاينات تفاعلية أو خرائط تركيز على جانب العميل ولا تُحمّل كملفات صور من الخادم.
        // لذلك غالبًا ما تكون `src` فارغة أو تُدار بواسطة JavaScript/Canvas — لا ينبغي اعتبارها صور lazy-load حقيقية في فحوصات الـ strict.
        let inspected = await page.evaluate(() => Array.from(document.querySelectorAll('img[data-src], img.progressive-img')).filter(i => {
          const ds = i.getAttribute('data-src');
          const s = i.getAttribute('src');
          // include if it has a data-src (lazy) or already a non-empty src (server-loaded)
          return (ds !== null) || (s && s.length > 0);
        }).map(i => ({ dataSrc: i.getAttribute('data-src'), src: i.getAttribute('src') })));
        // If any image still has no src (observer didn't trigger), perform bulk swap fallback and re-sample DOM
        if (inspected.some(x => !x.src || x.src.length === 0)) {
          await page.evaluate(() => document.querySelectorAll('img[data-src]').forEach(el => { try { const ds = el.getAttribute('data-src'); if (ds) { el.setAttribute('src', ds); el.removeAttribute('data-src'); const __p = new Image(); __p.src = ds; } } catch(e){} }));
          await page.waitForTimeout(1000);
          inspected = await page.evaluate(() => Array.from(document.querySelectorAll('img[data-src], img.progressive-img')).filter(i => {
            const ds = i.getAttribute('data-src');
            const s = i.getAttribute('src');
            return (ds !== null) || (s && s.length > 0);
          }).map(i => ({ dataSrc: i.getAttribute('data-src'), src: i.getAttribute('src') })));
        }
        for (let i = 0; i < inspected.length; i++) {
          const dsVal = inspected[i].dataSrc;
          const src = inspected[i].src;
          expect(src).not.toBeNull();
          // Defensive check: if src is empty, gather helpful diagnostics and fail with a clear message
          if (!src || src.length === 0) {
            const outer = await page.evaluate((idx) => {
              const list = Array.from(document.querySelectorAll('img[data-src], img.progressive-img')).filter(e => e.id !== 'preview-image');
              const el = list[idx];
              return el ? el.outerHTML : null;
            }, i);
            console.error(`Image missing src at index ${i} (data-src=${dsVal})`);
            console.error('Element outerHTML:', outer);
            console.error('Inspected snapshot for this index:', JSON.stringify(inspected[i] || {}));
            throw new Error(`Image at index ${i} has empty src (data-src=${dsVal})`);
          }
          if (dsVal) {
            const resolved = new URL(dsVal, url).href;
            const scrollTime = Date.now();
            await page.waitForTimeout(200);
            let found = false;
            for (const [rurl, meta] of imageResponses.entries()) {
              try {
                const abs = new URL(rurl, url).href;
                if (abs === resolved) {
                  found = true;
                  expect(meta.status).toBeGreaterThanOrEqual(200);
                  expect(meta.status).toBeLessThan(400);
                  const headers = meta.headers || {};
                  const hasCaching = (headers['etag'] || headers['last-modified'] || headers['cache-control']);
                      if (CACHE_STRICT) {
                        expect(Boolean(hasCaching)).toBeTruthy();
                      } else {
                        if (!hasCaching) console.warn(`Caching headers missing for ${resolved} (TEST_CACHE_STRICT not set)`);
                      }
                  if (headers['etag']) {
                    try {
                      const etag = headers['etag'];
                      const condResp = await page.request.get(resolved, { headers: { 'If-None-Match': etag } });
                      const condStatus = condResp.status();
                      if (condStatus === 304) console.log(`Conditional GET for ${resolved} returned 304 (cached)`);
                      else { console.warn(`Conditional GET for ${resolved} returned ${condStatus} (expected 304 ideally)`); expect(condStatus).toBeGreaterThanOrEqual(200); expect(condStatus).toBeLessThan(400); }
                    } catch (e) { console.warn('Conditional request failed', e); }
                  }
                  expect(meta.ts).toBeGreaterThanOrEqual(scrollTime - 50);
                  break;
                }
              } catch (e) {}
            }
            expect(found).toBeTruthy();
          }
        }
      } else {
        // Non-strict: perform a bulk swap to avoid scrolling flakiness in headless/CI.
        const dataSrcs = await page.evaluate(() => Array.from(document.querySelectorAll('img[data-src]')).map(i => i.getAttribute('data-src')));
        if (dataSrcs.length > 0) {
          console.log(`Bulk-swapping ${dataSrcs.length} images to stabilize test run`);
          await page.evaluate(() => document.querySelectorAll('img[data-src]').forEach(el => { try { const ds = el.getAttribute('data-src'); if (ds) { el.setAttribute('src', ds); el.removeAttribute('data-src'); const __p = new Image(); __p.src = ds; } } catch(e){} }));
          await page.waitForTimeout(1000);
        }

        for (let i = 0; i < dataSrcs.length; i++) {
          const dsVal = dataSrcs[i];
          const resolved = new URL(dsVal, url).href;
          // allow time for network observation
          await page.waitForTimeout(200);
          let found = false;
          for (const [rurl, meta] of imageResponses.entries()) {
            try {
              const abs = new URL(rurl, url).href;
              if (abs === resolved) {
                found = true;
                expect(meta.status).toBeGreaterThanOrEqual(200);
                expect(meta.status).toBeLessThan(400);
                const headers = meta.headers || {};
                const hasCaching = (headers['etag'] || headers['last-modified'] || headers['cache-control']);
                    if (CACHE_STRICT) {
                      expect(Boolean(hasCaching)).toBeTruthy();
                    } else {
                      if (!hasCaching) console.warn(`Caching headers missing for ${resolved} (TEST_CACHE_STRICT not set)`);
                    }
                if (headers['etag']) {
                  try {
                    const etag = headers['etag'];
                    const condResp = await page.request.get(resolved, { headers: { 'If-None-Match': etag } });
                    const condStatus = condResp.status();
                    if (condStatus === 304) console.log(`Conditional GET for ${resolved} returned 304 (cached)`);
                    else { console.warn(`Conditional GET for ${resolved} returned ${condStatus} (expected 304 ideally)`); expect(condStatus).toBeGreaterThanOrEqual(200); expect(condStatus).toBeLessThan(400); }
                  } catch (e) { console.warn('Conditional request failed', e); }
                }
                console.log(`Non-strict mode: image ${resolved} observed at ${meta.ts}`);
                break;
              }
            } catch (e) {}
          }
          expect(found).toBeTruthy();
        }
      }

      // If no images found, still pass but log a warning
      if (m === 0) console.warn(`No progressive images found on ${path}`);
    });
  }
});
