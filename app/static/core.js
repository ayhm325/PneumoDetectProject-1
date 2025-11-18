/**
 * Core.js - مكتبة أساسية موحدة
 * توفر وظائف مشتركة وواجهات برمجية للتطبيق
 */

const PneumoApp = (function() {
    'use strict';

    // ===== إعدادات تطبيق =====
    const CONFIG = {
        apiBase: '/api',
        timeout: 30000,
        debug: true,
        language: document.documentElement.lang || 'ar',
        theme: localStorage.getItem('theme') || 'light'
    };

    // ===== State Management =====
    const state = {
        user: null,
        isLoading: false,
        notifications: [],
        csrfToken: null,
        loginAttempts: parseInt(localStorage.getItem('loginAttempts') || '0'),
        maxLoginAttempts: 3,
        patientData: {
            analyses: [],
            stats: {
                total: 0,
                pending: 0,
                reviewed: 0,
                pneumonia: 0
            },
            pagination: {
                page: 1,
                per_page: 9,
                total: 0,
                pages: 1
            }
        },
        adminData: {
            users: [],
            analyses: [],
            stats: {
                total_users: 0,
                total_analyses: 0,
                pneumonia_cases: 0,
                accuracy: 0
            },
            settings: {
                max_file_size: 50,
                daily_limit: 100,
                min_confidence: 70
            }
        }
    };

    // ===== Utility Functions =====
    const Utils = {
        /**
         * تسجيل الأخطاء والعمليات
         */
        log: (level, message, data = null) => {
            if (!CONFIG.debug && level === 'debug') return;
            const timestamp = new Date().toISOString();
            const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
            console.log(`${prefix} ${message}`, data || '');
        },

        /**
         * إظهار إشعارات للمستخدم
         */
        notify: (message, type = 'info', duration = 4000, title = '') => {
            const notification = {
                id: Date.now(),
                message,
                title,
                type, // info, success, warning, error
                duration
            };
            
            state.notifications.push(notification);
            
            // إنشاء عنصر الإشعار
            const el = document.createElement('div');
            el.className = `notification ${type}`;
            
            const icon = type === 'error' ? 'fa-exclamation-circle' : 
                        type === 'success' ? 'fa-check-circle' : 
                        type === 'warning' ? 'fa-exclamation-triangle' : 'fa-info-circle';
            
            el.innerHTML = `
                <i class="fas ${icon}"></i>
                <div class="notification-content">
                    ${title ? `<div class="notification-title">${title}</div>` : ''}
                    <div class="notification-message">${message}</div>
                </div>
                <i class="fas fa-times notification-close" onclick="this.parentElement.remove()"></i>
            `;
            el.setAttribute('role', 'alert');
            
            // إضافة إلى الصفحة
            const container = document.getElementById('notification-container') || 
                            document.body;
            container.appendChild(el);
            
            // إزالة بعد المدة المحددة
            setTimeout(() => {
                el.classList.add('fade-out');
                setTimeout(() => el.remove(), 300);
                state.notifications = state.notifications.filter(n => n.id !== notification.id);
            }, duration);

            Utils.log('info', `Notification: ${type}`, message);
        },

        /**
         * إخفاء/إظهار عناصر التحميل
         */
        setLoading: (isLoading, message = 'جاري المعالجة...') => {
            state.isLoading = isLoading;
            const loader = document.querySelector('[role="loading"]');
            
            if (loader) {
                if (isLoading) {
                    loader.classList.add('active');
                    if (message) loader.textContent = message;
                } else {
                    loader.classList.remove('active');
                }
            }
        },

        /**
         * التحقق من صحة البريد الإلكتروني
         */
        isValidEmail: (email) => {
            const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return pattern.test(email);
        },

        /**
         * إزالة المسافات الزائدة والأحرف الخاصة
         */
        sanitize: (str) => {
            if (typeof str !== 'string') return '';
            return str.trim().replace(/[<>"']/g, '');
        },

        /**
         * تنسيق التاريخ
         */
        formatDate: (date, format = 'short') => {
            if (!(date instanceof Date)) date = new Date(date);
            const options = format === 'short' 
                ? { year: 'numeric', month: '2-digit', day: '2-digit' }
                : { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' };
            return new Intl.DateTimeFormat('ar-SA', options).format(date);
        },

        /**
         * الحصول على قيمة ترجمة
         */
        t: (key) => {
            const lang = document.documentElement.lang || 'ar';
            const translations = window.translations || {};
            return translations[lang] && translations[lang][key] ? translations[lang][key] : key;
        },

        /**
         * تحريك العداد الرقمي
         */
        animateCounter: (elementId, target, duration = 1000) => {
            const element = document.getElementById(elementId);
            if (!element) return;
            
            const start = parseInt(element.textContent) || 0;
            const increment = (target - start) / (duration / 30);
            let current = start;
            
            const timer = setInterval(() => {
                current += increment;
                if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
                    element.textContent = target;
                    clearInterval(timer);
                } else {
                    element.textContent = Math.round(current);
                }
            }, 30);
        }
    };

    // ===== API Module =====
    const API = {
        /**
         * طلب HTTP عام
         */
        request: async (method, endpoint, data = null, options = {}) => {
            try {
                Utils.setLoading(true);
                
                const url = `${CONFIG.apiBase}${endpoint}`;
                const fetchOptions = {
                    method: method.toUpperCase(),
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': state.csrfToken || '',
                        'XSRF-TOKEN': state.csrfToken || ''
                    },
                    credentials: 'include',
                    timeout: CONFIG.timeout,
                    ...options
                };

                if (data && ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
                    fetchOptions.body = JSON.stringify(data);
                }

                Utils.log('debug', `API Request: ${method.toUpperCase()} ${url}`, data);

                const response = await fetch(url, fetchOptions);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                const result = await response.json();
                Utils.log('debug', `API Response: ${url}`, result);
                Utils.setLoading(false);
                
                return { success: true, data: result };
            } catch (error) {
                Utils.log('error', 'API Error', error.message);
                Utils.notify(error.message || Utils.t('error_network'), 'error');
                Utils.setLoading(false);
                return { success: false, error: error.message };
            }
        },

        get: (endpoint, options) => API.request('GET', endpoint, null, options),
        post: (endpoint, data, options) => API.request('POST', endpoint, data, options),
        put: (endpoint, data, options) => API.request('PUT', endpoint, data, options),
        delete: (endpoint, options) => API.request('DELETE', endpoint, null, options)
    };

    // ===== DOM Module =====
    const DOM = {
        /**
         * الحصول على عنصر من الـ DOM مع معالجة الأخطاء
         */
        get: (selector) => {
            const el = document.querySelector(selector);
            if (!el && CONFIG.debug) {
                Utils.log('warn', `Element not found: ${selector}`);
            }
            return el;
        },

        /**
         * إضافة عنصر إلى الـ DOM
         */
        create: (tag, className = '', innerHTML = '') => {
            const el = document.createElement(tag);
            if (className) el.className = className;
            if (innerHTML) el.innerHTML = innerHTML;
            return el;
        },

        /**
         * تعيين معالجات الأحداث
         */
        on: (selector, event, handler) => {
            const els = document.querySelectorAll(selector);
            els.forEach(el => el.addEventListener(event, handler));
        },

        /**
         * إزالة معالجات الأحداث
         */
        off: (selector, event, handler) => {
            const els = document.querySelectorAll(selector);
            els.forEach(el => el.removeEventListener(event, handler));
        },

        /**
         * تبديل فئة CSS
         */
        toggleClass: (selector, className) => {
            const el = DOM.get(selector);
            if (el) el.classList.toggle(className);
        },

        /**
         * تعديل النص
         */
        setText: (selector, text) => {
            const el = DOM.get(selector);
            if (el) el.textContent = text;
        },

        /**
         * إظهار/إخفاء العناصر
         */
        show: (selector) => {
            const el = DOM.get(selector);
            if (el) el.style.display = '';
        },

        hide: (selector) => {
            const el = DOM.get(selector);
            if (el) el.style.display = 'none';
        },

        /**
         * تحديث محتوى عنصر
         */
        html: (selector, content) => {
            const el = DOM.get(selector);
            if (el) el.innerHTML = content;
        }
    };

    // ===== Theme Module =====
    const Theme = {
        current: CONFIG.theme,

        init: () => {
            document.documentElement.setAttribute('data-theme', Theme.current);
        },

        toggle: () => {
            Theme.current = Theme.current === 'light' ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', Theme.current);
            localStorage.setItem('theme', Theme.current);
            Utils.log('info', `Theme switched to: ${Theme.current}`);
        }
    };

    // ===== Language Module =====
    const Language = {
        current: CONFIG.language,

        init: () => {
            // Set initial language from localStorage or browser
            const savedLang = localStorage.getItem('pneumoDetectLang') || CONFIG.language;
            Language.set(savedLang);
        },

        set: (lang) => {
            Language.current = lang;
            localStorage.setItem('pneumoDetectLang', lang);
            document.documentElement.lang = lang;
            document.documentElement.dir = lang === 'ar' ? 'rtl' : 'ltr';
            
            // Update language toggle buttons
            document.querySelectorAll('.lang-toggle button').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-lang') === lang);
                btn.setAttribute('aria-pressed', btn.getAttribute('data-lang') === lang ? 'true' : 'false');
            });
            
            // Update translated elements
            document.querySelectorAll('[data-i18n]').forEach(element => {
                const key = element.getAttribute('data-i18n');
                if (window.translations && window.translations[lang] && window.translations[lang][key]) {
                    element.textContent = window.translations[lang][key];
                }
            });
            
            Utils.log('info', `Language switched to: ${lang}`);
        }
    };

    // ===== Index Module =====
    const Index = {
        // Flag to prevent duplicate submissions
        isAnalyzing: false,

        /**
         * تهيئة صفحة الرئيسية
         */
        init: () => {
            // إضافة مستمعي الأحداث
            const themeToggle = DOM.get('#theme-toggle');
            const uploadArea = DOM.get('#file-upload-area');
            const imageInput = DOM.get('#imageInput');
            const sampleImageBtn = DOM.get('.btn-secondary');

            if (themeToggle) {
                themeToggle.addEventListener('click', Theme.toggle);
            }

            if (uploadArea && imageInput) {
                uploadArea.addEventListener('click', () => imageInput.click());
                uploadArea.addEventListener('keypress', (e) => { 
                    if (e.key === 'Enter' || e.key === ' ') { 
                        e.preventDefault(); 
                        imageInput.click(); 
                    } 
                });
                
                uploadArea.addEventListener('dragover', (e) => { 
                    e.preventDefault(); 
                    uploadArea.classList.add('drag-over'); 
                });
                
                uploadArea.addEventListener('dragleave', () => uploadArea.classList.remove('drag-over'));
                
                uploadArea.addEventListener('drop', (e) => { 
                    e.preventDefault(); 
                    uploadArea.classList.remove('drag-over'); 
                    Index.handleFile(e.dataTransfer.files[0]); 
                });
                
                imageInput.addEventListener('change', (e) => { 
                    if (e.target.files.length) Index.handleFile(e.target.files[0]); 
                });
            }

            if (sampleImageBtn) {
                sampleImageBtn.addEventListener('click', Index.loadSampleImage);
            }

            // Lazy load hero background
            Index.lazyLoadBackground();
        },

        /**
         * معالجة الملف المرفوع
         */
        handleFile: (file) => {
            if (!file) return;
            const maxSize = 50 * 1024 * 1024;
            const allowedTypes = ['image/jpeg', 'image/png'];

            if (!allowedTypes.includes(file.type)) {
                Utils.notify(Utils.t('error_invalid_file'), 'error');
                return;
            }
            if (file.size > maxSize) {
                Utils.notify(Utils.t('error_file_too_large'), 'error');
                return;
            }
            
            Utils.notify(`تم اختيار الملف: ${file.name}`, 'success');
            Index.startAnalysis(file);
        },

        /**
         * تحميل صورة نموذجية - محسّن
         */
        loadSampleImage: () => {
            Utils.notify('جاري تحميل صورة المثال...', 'info');
            
            // Create a proper image blob using a data URL
            const canvas = document.createElement('canvas');
            canvas.width = 256;
            canvas.height = 256;
            const ctx = canvas.getContext('2d');
            
            // Draw a simple medical-like image (grayscale pattern)
            ctx.fillStyle = '#a0a0a0';
            ctx.fillRect(0, 0, 256, 256);
            
            // Add some pattern to simulate X-ray
            ctx.fillStyle = '#d0d0d0';
            ctx.beginPath();
            ctx.ellipse(128, 128, 80, 100, 0, 0, Math.PI * 2);
            ctx.fill();
            
            ctx.fillStyle = '#808080';
            ctx.beginPath();
            ctx.ellipse(128, 128, 60, 80, 0, 0, Math.PI * 2);
            ctx.fill();
            
            // Convert canvas to blob and create file
            canvas.toBlob((blob) => {
                const sampleFile = new File([blob], 'sample_xray.jpg', { type: 'image/jpeg' });
                Index.startAnalysis(sampleFile);
            }, 'image/jpeg', 0.8);
        },

        /**
         * بدء تحليل الصورة - محسّن
         */
        startAnalysis: async (file) => {
            // Prevent duplicate submissions
            if (Index.isAnalyzing) {
                Utils.notify('جاري التحليل... يرجى الانتظار', 'warning');
                return;
            }

            const loadingState = DOM.get('#loading-state');
            const resultDiv = DOM.get('#analysis-result');
            const progressBar = DOM.get('#analysis-progress-bar');
            const progressText = DOM.get('#analysis-progress-text');

            loadingState.style.display = 'block';
            resultDiv.style.display = 'none';

            try {
                // Mark as analyzing
                Index.isAnalyzing = true;

                // Show progress animation
                progressBar.style.width = '10%';
                progressText.textContent = '10%';
                loadingState.setAttribute('aria-valuenow', 10);

                // Prepare form data with the file
                const formData = new FormData();
                formData.append('file', file);

                // Make real API call to /api/analyze
                Utils.notify('جاري تحليل الصورة بواسطة النموذج الذكي...', 'info');
                progressBar.style.width = '30%';
                progressText.textContent = '30%';
                loadingState.setAttribute('aria-valuenow', 30);

                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData,
                    credentials: 'include'
                });

                progressBar.style.width = '70%';
                progressText.textContent = '70%';
                loadingState.setAttribute('aria-valuenow', 70);

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.message || 'فشل التحليل');
                }

                const result = await response.json();
                
                progressBar.style.width = '100%';
                progressText.textContent = '100%';
                loadingState.setAttribute('aria-valuenow', 100);

                // Display results
                setTimeout(() => {
                    Index.displayAnalysisResult(result.data);
                    loadingState.style.display = 'none';
                    resultDiv.style.display = 'block';
                    resultDiv.scrollIntoView({ behavior: 'smooth' });
                    Utils.notify('تم التحليل بنجاح!', 'success');
                }, 500);

            } catch (error) {
                loadingState.style.display = 'none';
                Utils.notify('خطأ: ' + error.message, 'error');
                console.error('Analysis error:', error);
            } finally {
                // Mark as not analyzing
                Index.isAnalyzing = false;
            }
        },

        /**
         * عرض نتائج التحليل - محسّن
         */
        displayAnalysisResult: (data) => {
            const resultCardContent = DOM.get('#result-card-content');
            if (!resultCardContent) return;

            const resultBadge = data.result === 'PNEUMONIA' ? 
                '<p style="color: #dc3545; font-weight: bold;">🔴 إيجابي (التهاب رئوي)</p>' :
                '<p style="color: #28a745; font-weight: bold;">🟢 سلبي (بدون التهاب)</p>';

            resultCardContent.innerHTML = `
                <div class="result-item">
                    <label>النتيجة:</label>
                    ${resultBadge}
                </div>
                <div class="result-item">
                    <label>درجة الثقة:</label>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${data.confidence}%"></div>
                    </div>
                    <p class="confidence-text">${data.confidence.toFixed(1)}%</p>
                </div>
                <div class="result-item">
                    <label>الشرح:</label>
                    <p>${data.explanation || 'تم تحليل الصورة بواسطة نموذج الذكاء الاصطناعي المتقدم'}</p>
                </div>
                ${data.saliency_url ? `
                <div class="result-item">
                    <label>خريطة الإبراز (Saliency Map):</label>
                    <img src="${data.saliency_url}" alt="خريطة الإبراز" style="max-width: 100%; border-radius: 8px; margin-top: 10px;">
                </div>
                ` : ''}
            `;
        },

        /**
         * تحميل الخلفية بشكل متأخر - محسّن
         */
        lazyLoadBackground: () => {
            const heroSection = DOM.get('#home-section');
            if (!heroSection) return;
            
            const bgUrl = heroSection.getAttribute('data-bg');
            if (!bgUrl) return;
            
            const img = new Image();
            img.onload = function() {
                heroSection.style.backgroundImage = `url(${bgUrl})`;
                heroSection.classList.add('lazy-bg');
            };
            img.src = bgUrl;
        }
    };

    // ===== Forms Module =====
    const Forms = {
        /**
         * التحقق من صحة نموذج تسجيل الدخول
         */
        validateLoginForm: (formSelector) => {
            const form = DOM.get(formSelector);
            if (!form) return false;

            let isValid = true;
            
            // التحقق من اسم المستخدم
            const username = DOM.get('#login-username');
            if (username && !Forms.validateField(username, { required: true, minLength: 3 })) {
                isValid = false;
            }
            
            // التحقق من كلمة المرور
            const password = DOM.get('#login-password');
            if (password && !Forms.validateField(password, { required: true, minLength: 6 })) {
                isValid = false;
            }

            return isValid;
        },

        /**
         * التحقق من صحة نموذج إضافة مستخدم
         */
        validateAddUserForm: (formSelector) => {
            const form = DOM.get(formSelector);
            if (!form) return false;

            let isValid = true;
            
            // التحقق من اسم المستخدم
            const username = DOM.get('#new-username');
            if (username && !Forms.validateField(username, { required: true, minLength: 3 })) {
                isValid = false;
            }
            
            // التحقق من البريد الإلكتروني
            const email = DOM.get('#new-email');
            if (email && !Forms.validateField(email, { required: true, type: 'email' })) {
                isValid = false;
            }
            
            // التحقق من الدور
            const role = DOM.get('#new-role');
            if (role && !Forms.validateField(role, { required: true })) {
                isValid = false;
            }

            return isValid;
        },

        /**
         * التحقق من حقل واحد
         */
        validateField: (field, options = {}) => {
            const value = field.value.trim();
            const { required, type, minLength, maxLength } = options;

            // التحقق من الحقول المطلوبة
            if (required && !value) {
                Forms.setError(field, Utils.t('error_required_field'));
                return false;
            }

            // التحقق من الحد الأدنى للطول
            if (minLength && value.length < minLength) {
                Forms.setError(field, Utils.t('error_min_length').replace('{min}', minLength));
                return false;
            }

            // التحقق من الحد الأقصى للطول
            if (maxLength && value.length > maxLength) {
                Forms.setError(field, Utils.t('error_max_length').replace('{max}', maxLength));
                return false;
            }

            // التحقق من البريد الإلكتروني
            if (type === 'email' && value && !Utils.isValidEmail(value)) {
                Forms.setError(field, Utils.t('error_invalid_email'));
                return false;
            }

            Forms.clearError(field);
            return true;
        },

        /**
         * عرض رسالة خطأ
         */
        setError: (field, message) => {
            field.classList.add('error');
            let errorEl = field.nextElementSibling;
            
            if (!errorEl || !errorEl.classList.contains('error-text')) {
                errorEl = DOM.create('span', 'error-text', message);
                field.after(errorEl);
            } else {
                errorEl.textContent = message;
            }
        },

        /**
         * مسح رسالة الخطأ
         */
        clearError: (field) => {
            field.classList.remove('error');
            const errorEl = field.nextElementSibling;
            if (errorEl && errorEl.classList.contains('error-text')) {
                errorEl.remove();
            }
        },

        /**
         * الحصول على بيانات النموذج
         */
        getFormData: (formSelector) => {
            const form = DOM.get(formSelector);
            if (!form) return null;

            const formData = new FormData(form);
            const data = {};

            for (const [key, value] of formData.entries()) {
                data[key] = value;
            }

            return data;
        },

        /**
         * تبديل إظهار كلمة المرور - محسّن لواجهة تسجيل الدخول
         */
        togglePasswordVisibility: (inputId, buttonId) => {
            const input = DOM.get(`#${inputId}`);
            const button = DOM.get(`#${buttonId}`);
            const passwordGroup = DOM.get('#password-group');
            
            if (!input || !button) return;
            
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            
            // تحديث الأيقونة والحالة
            const icon = button.querySelector('i');
            if (type === 'password') {
                icon.className = 'fas fa-eye';
                passwordGroup.classList.remove('password-visible');
            } else {
                icon.className = 'fas fa-eye-slash';
                passwordGroup.classList.add('password-visible');
            }
            
            button.setAttribute('aria-pressed', type === 'text');
            
            // إضافة تأثير بصري عند النقر
            button.style.transform = 'scale(0.9)';
            setTimeout(() => {
                button.style.transform = 'scale(1)';
            }, 100);
        }
    };

    // ===== Auth Module =====
    const Auth = {
        /**
         * الحصول على بيانات المستخدم الحالي
         */
        getCurrentUser: () => state.user,

        /**
         * تسجيل الدخول - محسّن لواجهة تسجيل الدخول
         */
        login: async (username, password, rememberMe = false) => {
            // التحقق من محاولات تسجيل الدخول
            if (state.loginAttempts >= state.maxLoginAttempts) {
                Utils.notify(Utils.t('error_account_locked'), 'error');
                return false;
            }

            const result = await API.post('/auth/login', { username, password, remember_me: rememberMe });
            
            if (result.success) {
                state.user = result.data.user;
                state.loginAttempts = 0;
                localStorage.setItem('loginAttempts', '0');
                Utils.notify(Utils.t('success_login'), 'success');
                return true;
            } else {
                // زيادة عدد المحاولات الفاشلة
                state.loginAttempts++;
                localStorage.setItem('loginAttempts', state.loginAttempts.toString());
                
                // عرض رسالة الخطأ مع عدد المحاولات المتبقية
                const remainingAttempts = state.maxLoginAttempts - state.loginAttempts;
                if (remainingAttempts > 0) {
                    const errorMsg = result.error || Utils.t('error_invalid_credentials');
                    const attemptText = `${errorMsg} (${remainingAttempts} ${Utils.t('remaining_attempts')})`;
                    Utils.notify(attemptText, 'error');
                    
                    // تحديث رسالة التحذير في الواجهة
                    const attemptFeedback = DOM.get('#attempt-feedback');
                    const attemptTextEl = DOM.get('#attempt-text');
                    if (attemptFeedback && attemptTextEl) {
                        attemptFeedback.style.display = 'flex';
                        attemptTextEl.textContent = attemptText;
                    }
                } else {
                    // قفل الحساب
                    Utils.notify(Utils.t('error_account_locked'), 'error');
                    
                    // تحديث رسالة القفل في الواجهة
                    const attemptFeedback = DOM.get('#attempt-feedback');
                    const attemptTextEl = DOM.get('#attempt-text');
                    const loginBtn = DOM.get('#login-btn');
                    
                    if (attemptFeedback && attemptTextEl) {
                        attemptFeedback.style.display = 'flex';
                        attemptTextEl.textContent = Utils.t('error_account_locked');
                    }
                    
                    if (loginBtn) {
                        loginBtn.disabled = true;
                    }
                }
                
                return false;
            }
        },

        /**
         * تسجيل الخروج
         */
        logout: async () => {
            const result = await API.post('/auth/logout');
            if (result.success) {
                state.user = null;
                Utils.notify(Utils.t('success_logout'), 'info');
                return true;
            }
            return false;
        },

        /**
         * التحقق من أن المستخدم مسجل دخول
         */
        isAuthenticated: () => state.user !== null,

        /**
         * التحقق من حالة قفل الحساب
         */
        isAccountLocked: () => state.loginAttempts >= state.maxLoginAttempts,

        /**
         * إعادة تعيين محاولات تسجيل الدخول
         */
        resetLoginAttempts: () => {
            state.loginAttempts = 0;
            localStorage.setItem('loginAttempts', '0');
        }
    };

    // ===== Login Module =====
    const Login = {
        /**
         * تهيئة صفحة تسجيل الدخول
         */
        init: () => {
            // التحقق من حالة الحساب عند تحميل الصفحة
            if (Auth.isAccountLocked()) {
                const attemptFeedback = DOM.get('#attempt-feedback');
                const attemptTextEl = DOM.get('#attempt-text');
                const loginBtn = DOM.get('#login-btn');
                
                if (attemptFeedback && attemptTextEl) {
                    attemptFeedback.style.display = 'flex';
                    attemptTextEl.textContent = Utils.t('error_account_locked');
                }
                
                if (loginBtn) {
                    loginBtn.disabled = true;
                }
            }

            // إضافة مستمعي الأحداث
            const form = DOM.get('#login-form');
            const toggleBtn = DOM.get('#toggle-password');
            const themeToggle = DOM.get('#theme-toggle');

            if (form) {
                form.addEventListener('submit', Login.handleSubmit);
            }

            if (toggleBtn) {
                toggleBtn.addEventListener('click', () => {
                    Forms.togglePasswordVisibility('login-password', 'toggle-password');
                });
            }

            if (themeToggle) {
                themeToggle.addEventListener('click', Theme.toggle);
            }
        },

        /**
         * معالجة إرسال نموذج تسجيل الدخول
         */
        handleSubmit: async (e) => {
            e.preventDefault();
            
            const username = DOM.get('#login-username').value.trim();
            const password = DOM.get('#login-password').value;
            const rememberMe = DOM.get('#remember-me').checked;
            
            // التحقق من صحة النموذج
            if (!Forms.validateLoginForm('#login-form')) {
                Utils.notify(Utils.t('error_form_validation'), 'error');
                return;
            }
            
            // إظهار حالة التحميل
            const loginBtn = DOM.get('#login-btn');
            const originalBtnContent = loginBtn.innerHTML;
            loginBtn.disabled = true;
            loginBtn.innerHTML = '<span class="loading-spinner"></span> جاري التحقق...';
            
            try {
                // محاولة تسجيل الدخول
                const success = await Auth.login(username, password, rememberMe);
                
                if (success) {
                    // التوجيه بناءً على دور المستخدم
                    const redirectUrl = Auth.getCurrentUser().role === 'doctor' ? '/doctor' : 
                                        Auth.getCurrentUser().role === 'admin' ? '/admin' : '/patient';
                    
                    // الانتظار قليلاً لعرض رسالة النجاح
                    setTimeout(() => {
                        window.location.replace(redirectUrl);
                    }, 1500);
                }
            } finally {
                // استعادة حالة الزر إذا لم يتم قفل الحساب
                if (!Auth.isAccountLocked()) {
                    loginBtn.disabled = false;
                    loginBtn.innerHTML = originalBtnContent;
                }
            }
        }
    };

    // ===== Patient Module =====
    const Patient = {
        /**
         * تهيئة صفحة المريض
         */
        init: () => {
            // إضافة مستمعي الأحداث
            const themeToggle = DOM.get('#theme-toggle');
            const statusFilter = DOM.get('#status-filter');
            const sortFilter = DOM.get('#sort-filter');

            if (themeToggle) {
                themeToggle.addEventListener('click', Theme.toggle);
            }

            if (statusFilter) {
                statusFilter.addEventListener('change', () => {
                    Patient.loadAnalyses(1);
                });
            }

            if (sortFilter) {
                sortFilter.addEventListener('change', () => {
                    Patient.loadAnalyses(1);
                });
            }

            // تحميل التحاليل عند تحميل الصفحة
            Patient.loadAnalyses();
        },

        /**
         * عرض محملات الهيكل العظمي
         */
        showSkeletonLoaders: (count) => {
            const container = DOM.get('#results-list');
            if (!container) return;
            
            container.innerHTML = '';
            
            for (let i = 0; i < count; i++) {
                const skeleton = DOM.create('div', 'skeleton-card');
                skeleton.innerHTML = `
                    <div class="skeleton-header skeleton"></div>
                    <div class="skeleton-content">
                        <div class="skeleton-image skeleton"></div>
                        <div class="skeleton-text skeleton"></div>
                        <div class="skeleton-text skeleton short"></div>
                    </div>
                    <div class="skeleton-actions skeleton"></div>
                `;
                container.appendChild(skeleton);
            }
        },

        /**
         * تحميل تحاليل المريض
         */
        loadAnalyses: async (page = 1) => {
            const resultsList = DOM.get('#results-list');
            const emptyState = DOM.get('#empty-state');
            const pagination = DOM.get('#pagination');
            
            if (!resultsList) return;
            
            // عرض محملات الهيكل العظمي
            Patient.showSkeletonLoaders(state.patientData.pagination.per_page);
            
            if (emptyState) DOM.hide(emptyState);
            if (pagination) DOM.hide(pagination);

            try {
                const status = DOM.get('#status-filter')?.value || 'all';
                const sort = DOM.get('#sort-filter')?.value || 'recent';
                
                // استدعاء API حقيقي لـ /api/patient/analyses
                const result = await API.get(`/patient/analyses?page=${page}&status=${status}&sort=${sort}`);
                
                if (result.success) {
                    state.patientData.analyses = result.data.items || [];
                    state.patientData.pagination = {
                        page: result.data.page || 1,
                        per_page: result.data.per_page || 9,
                        total: result.data.total || 0,
                        pages: result.data.pages || 1
                    };
                    
                    if (state.patientData.analyses.length === 0) {
                        DOM.hide(resultsList);
                        if (emptyState) DOM.show(emptyState);
                    } else {
                        DOM.show(resultsList);
                        if (emptyState) DOM.hide(emptyState);
                        Patient.displayResults(state.patientData.analyses);
                        Patient.updateStats();
                        Patient.updatePagination();
                    }
                }
            } catch (error) {
                Utils.log('error', 'Error loading patient analyses:', error);
                Utils.notify(Utils.t('error_network'), 'error');
                if (resultsList) {
                    resultsList.innerHTML = `<p class="error-message">${Utils.t('error_loading_data')}</p>`;
                }
            }
        },

        /**
         * عرض النتائج
         */
        displayResults: (results) => {
            const container = DOM.get('#results-list');
            if (!container) return;
            
            const lang = document.documentElement.lang || 'ar';
            
            container.innerHTML = results.map(result => `
                <div class="result-card">
                    <div class="result-header">
                        <div class="result-title">
                            <h4>تحليل #${result.id}</h4>
                            <div class="patient-info">
                                <i class="fas fa-user"></i> 
                                ${result.patient_username}
                            </div>
                        </div>
                        <span class="result-status ${result.review_status === 'pending' ? 'status-pending' : 'status-reviewed'}">
                            <i class="fas fa-${result.review_status === 'pending' ? 'hourglass-half' : 'check-circle'}"></i>
                            ${result.review_status === 'pending' ? Utils.t('filter_pending') : Utils.t('filter_reviewed')}
                        </span>
                    </div>

                    <div class="result-content">
                        <div class="result-image">
                            <img src="${result.image_url}" alt="صورة أشعة سينية" onerror="this.onerror=null;this.src='https://picsum.photos/seed/placeholder/400/300.jpg';">
                        </div>
                        <div class="result-details">
                            <div class="detail-row">
                                <div class="detail-label" data-i18n="result_analysis_label">النتيجة:</div>
                                <div class="detail-value">
                                    ${result.model_result === 'PNEUMONIA' ? '🔴 التهاب رئوي' : '🟢 سليم'}
                                </div>
                            </div>
                            
                            <div class="detail-row">
                                <div class="detail-label" data-i18n="result_confidence_label">درجة الثقة:</div>
                                <div class="detail-value">${(result.confidence).toFixed(1)}%</div>
                            </div>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: ${result.confidence}%"></div>
                            </div>

                            ${result.doctor_notes ? `
                                <div class="detail-row">
                                    <div class="detail-label" data-i18n="doctor_notes_label">ملاحظات الطبيب:</div>
                                    <div class="detail-value">${result.doctor_notes}</div>
                                </div>
                            ` : ''}
                        </div>
                    </div>

                    <div class="result-actions">
                        <button class="btn btn-primary" onclick="Patient.viewDetails('${result.id}')" aria-label="عرض تفاصيل التحليل" tabindex="0">
                            <i class="fas fa-eye" aria-hidden="true"></i> 
                            <span data-i18n="view_details_btn">عرض التفاصيل</span>
                        </button>
                        <button class="btn btn-secondary" onclick="Patient.downloadResult('${result.id}')" aria-label="تحميل نتيجة التحليل" tabindex="0">
                            <i class="fas fa-download" aria-hidden="true"></i> 
                            <span data-i18n="download_btn">تحميل</span>
                        </button>
                    </div>
                </div>
            `).join('');
        },

        /**
         * تحديث الإحصائيات
         */
        updateStats: () => {
            const total = state.patientData.pagination.total;
            const pending = state.patientData.analyses.filter(i => i.review_status === 'pending').length;
            const reviewed = state.patientData.analyses.filter(i => i.review_status === 'reviewed').length;
            const pneumonia = state.patientData.analyses.filter(i => i.model_result === 'PNEUMONIA').length;

            // تحريك عداد التحديث
            Utils.animateCounter('total-analyses', total);
            Utils.animateCounter('pending-count', pending);
            Utils.animateCounter('reviewed-count', reviewed);
            Utils.animateCounter('pneumonia-count', pneumonia);
        },

        /**
         * تحديث الترحيل
         */
        updatePagination: () => {
            const pagination = DOM.get('#pagination');
            if (!pagination) return;
            
            const { page, pages } = state.patientData.pagination;
            
            if (pages <= 1) {
                DOM.hide(pagination);
                return;
            }

            let html = '';
            
            if (page > 1) {
                html += `<button onclick="Patient.loadAnalyses(${page - 1})" aria-label="الصفحة السابقة" role="button" tabindex="0">${Utils.t('pagination_prev') || 'السابقة'}</button>`;
            }

            for (let i = 1; i <= pages; i++) {
                html += `<button onclick="Patient.loadAnalyses(${i})" ${i === page ? 'class="active"' : ''} aria-label="الصفحة ${i}" role="button" tabindex="0">${i}</button>`;
            }

            if (page < pages) {
                html += `<button onclick="Patient.loadAnalyses(${page + 1})" aria-label="الصفحة التالية" role="button" tabindex="0">${Utils.t('pagination_next') || 'التالية'}</button>`;
            }

            DOM.html(pagination, html);
            DOM.show(pagination);
        },

        /**
         * عرض تفاصيل التحليل
         */
        viewDetails: (resultId) => {
            // في تطبيق حقيقي، هذا سينتقل إلى صفحة التفاصيل
            Utils.notify(`عرض تفاصيل التحليل #${resultId}`, 'info');
        },

        /**
         * تحميل نتيجة التحليل
         */
        downloadResult: (resultId) => {
            // في تطبيق حقيقي، هذا سيبدأ التحميل
            Utils.notify(`جاري تحميل التحليل #${resultId}`, 'success');
        }
    };

    // ===== Doctor Module =====
    const Doctor = {
        /**
         * تهيئة صفحة الطبيب
         */
        init: () => {
            // إضافة مستمعي الأحداث
            const themeToggle = DOM.get('#theme-toggle');
            const statusFilter = DOM.get('#status-filter');
            const sortFilter = DOM.get('#sort-filter');

            if (themeToggle) {
                themeToggle.addEventListener('click', Theme.toggle);
            }

            if (statusFilter) {
                statusFilter.addEventListener('change', () => {
                    Doctor.loadAnalyses(1);
                });
            }

            if (sortFilter) {
                sortFilter.addEventListener('change', () => {
                    Doctor.loadAnalyses(1);
                });
            }

            // تحميل التحاليل عند تحميل الصفحة
            Doctor.loadAnalyses();
        },

        /**
         * عرض محملات الهيكل العظمي
         */
        showSkeletonLoaders: (count) => {
            const container = DOM.get('#analyses-list');
            if (!container) return;
            
            container.innerHTML = '';
            
            for (let i = 0; i < count; i++) {
                const skeleton = DOM.create('div', 'skeleton-card');
                skeleton.innerHTML = `
                    <div class="skeleton-header skeleton"></div>
                    <div class="skeleton-content">
                        <div class="skeleton-image skeleton"></div>
                        <div class="skeleton-text skeleton"></div>
                        <div class="skeleton-text skeleton short"></div>
                    </div>
                    <div class="skeleton-review skeleton"></div>
                `;
                container.appendChild(skeleton);
            }
        },

        /**
         * تحميل تحاليل الطبيب
         */
        loadAnalyses: async (page = 1) => {
            const listContainer = DOM.get('#analyses-list');
            const emptyState = DOM.get('#empty-state');
            const pagination = DOM.get('#pagination');
            
            if (!listContainer) return;
            
            // عرض محملات الهيكل العظمي
            Doctor.showSkeletonLoaders(6);
            
            if (emptyState) DOM.hide(emptyState);
            if (pagination) DOM.hide(pagination);

            try {
                const search = DOM.get('#patient-search').value.trim();
                const status = DOM.get('#status-filter').value;
                
                // استدعاء API حقيقي لـ /api/doctor/analyses
                const result = await API.get(`/api/doctor/analyses?page=${page}&status=${status}&patient=${search}`);
                
                if (result.success) {
                    const analyses = result.data?.items || [];
                    const paginationData = result.data?.pagination || { page: 1, per_page: 9, total: 0, pages: 1 };
                    
                    if (analyses.length === 0) {
                        DOM.hide(listContainer);
                        if (emptyState) DOM.show(emptyState);
                    } else {
                        DOM.show(listContainer);
                        if (emptyState) DOM.hide(emptyState);
                        Doctor.displayAnalyses(analyses);
                        Doctor.updateStats(analyses);
                        Doctor.updatePagination(paginationData);
                    }
                }
            } catch (error) {
                Utils.log('error', 'Error loading doctor analyses:', error);
                Utils.notify(Utils.t('error_network'), 'error');
                if (listContainer) {
                    listContainer.innerHTML = `<p class="error-message">${Utils.t('error_loading_data')}</p>`;
                }
            }
        },

        /**
         * عرض النتائج
         */
        displayAnalyses: (analyses) => {
            const container = DOM.get('#analyses-list');
            if (!container) return;
            
            const lang = document.documentElement.lang || 'ar';
            
            container.innerHTML = analyses.map((analysis, index) => `
                <div class="analysis-card doctor">
                    <div class="analysis-header">
                        <div class="analysis-title">
                            <h4>تحليل #${analysis.id}</h4>
                            <div class="patient-info">
                                <i class="fas fa-user"></i> 
                                ${analysis.patient_username}
                            </div>
                        </div>
                        <span class="analysis-status ${analysis.review_status === 'pending' ? 'status-pending' : 'status-reviewed'}">
                            <i class="fas fa-${analysis.review_status === 'pending' ? 'hourglass' : 'check'}"></i>
                            ${analysis.review_status === 'pending' ? Utils.t('filter_pending') : analysis.review_status === 'reviewed' ? Utils.t('filter_reviewed') : Utils.t('filter_rejected')}
                        </span>
                    </div>

                    <div class="analysis-content">
                        <div class="image-section">
                            <img src="${analysis.image_url}" alt="صورة أشعة سينية" onerror="this.onerror=null;this.src='https://picsum.photos/seed/placeholder/400/300.jpg';">
                        </div>
                        <div class="details-section">
                            <div class="detail-row">
                                <div class="detail-label" data-i18n="result_confidence_label">درجة الثقة:</div>
                                <div class="detail-value">${(analysis.confidence).toFixed(1)}%</div>
                            </div>
                            <div class="confidence-bar">
                                <div class="confidence-fill" style="width: ${analysis.confidence}%"></div>
                            </div>
                            
                            <div class="detail-row">
                                <div class="detail-label" data-i18n="result_analysis_label">التشخيص الأولي:</div>
                                <div class="detail-value">
                                    ${analysis.model_result === 'PNEUMONIA' ? '🔴 التهاب رئوي' : '🟢 سليم'}
                                </div>
                            </div>

                            <div class="diagnosis-box">
                                <h4 data-i18n="model_notes_title">📋 ملاحظات النموذج</h4>
                                <p>${analysis.explanation}</p>
                            </div>
                        </div>
                    </div>

                    <div class="review-section">
                        <h4 data-i18n="doctor_review_title">✍️ إضافة تقييمك الطبي</h4>
                        <form onsubmit="Doctor.submitReview(event, '${analysis.id}')">
                            <div class="form-group">
                                <label for="notes-${index}" data-i18n="doctor_notes_label">ملاحظاتك الطبية:</label>
                                <textarea 
                                    id="notes-${index}" 
                                    name="notes" 
                                    data-i18n-placeholder="doctor_notes_placeholder" 
                                    placeholder="أضف ملاحظاتك الطبية والتوصيات..."
                                    minlength="5"
                                    maxlength="5000"
                                    required
                                ></textarea>
                            </div>

                            <div class="review-actions">
                                <button type="submit" class="btn btn-approve" aria-label="موافقة وحفظ التقييم">
                                    <i class="fas fa-check-circle"></i> 
                                    <span data-i18n="approve_btn">موافقة وحفظ</span>
                                </button>
                                <button type="button" class="btn btn-reject" onclick="Doctor.openRejectModal('${analysis.id}')" aria-label="رفض التحليل">
                                    <i class="fas fa-times-circle"></i> 
                                    <span data-i18n="reject_btn">رفض</span>
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            `).join('');
        },

        /**
         * تحديث الإحصائيات
         */
        updateStats: (analyses) => {
            const pending = analyses.filter(i => i.review_status === 'pending').length;
            const reviewed = analyses.filter(i => i.review_status === 'reviewed').length;
            const pneumonia = analyses.filter(i => i.model_result === 'PNEUMONIA').length;

            // تحريك عداد التحديث
            Utils.animateCounter('pending-count', pending);
            Utils.animateCounter('reviewed-today', reviewed);
            Utils.animateCounter('pneumonia-count', pneumonia);
        },

        /**
         * تحديث الترحيل
         */
        updatePagination: (pagination) => {
            const paginationContainer = DOM.get('#pagination');
            if (!paginationContainer) return;
            
            const { page, pages } = pagination;
            
            if (pages <= 1) {
                DOM.hide(paginationContainer);
                return;
            }

            let html = '';
            
            if (page > 1) {
                html += `<button onclick="Doctor.loadAnalyses(${page - 1})" aria-label="الصفحة السابقة" role="button" tabindex="0">${Utils.t('pagination_prev') || 'السابقة'}</button>`;
            }

            for (let i = 1; i <= pages; i++) {
                html += `<button onclick="Doctor.loadAnalyses(${i})" ${i === page ? 'class="active"' : ''} aria-label="الصفحة ${i}" role="button" tabindex="0">${i}</button>`;
            }

            if (page < pages) {
                html += `<button onclick="Doctor.loadAnalyses(${page + 1})" aria-label="الصفحة التالية" role="button" tabindex="0">${Utils.t('pagination_next') || 'التالية'}</button>`;
            }

            DOM.html(paginationContainer, html);
            DOM.show(paginationContainer);
        },

        /**
         * فتح نافذة منبثقة لسبب الرفض
         */
        openRejectModal: (analysisId) => {
            const modal = DOM.get('#reject-modal');
            const messageEl = DOM.get('#modal-message');
            const confirmBtn = DOM.get('#confirm-btn');
            
            if (!modal || !messageEl || !confirmBtn) return;
            
            // حفظ معرف التحليل الحالي
            Doctor.currentAnalysisId = analysisId;
            
            messageEl.textContent = Utils.t('reject_analysis_title');
            confirmBtn.onclick = () => {
                Doctor.confirmReject();
            };
            
            modal.style.display = 'block';
            modal.setAttribute('aria-hidden', 'false');
            
            // التركيز على زر التأكيد
            setTimeout(() => {
                confirmBtn.focus();
            }, 100);
        },

        /**
         * إغلاق نافذة الرفض
         */
        closeRejectModal: () => {
            const modal = DOM.get('#reject-modal');
            if (!modal) return;
            
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
            DOM.get('#reject-reason').value = '';
        },

        /**
         * تأكيد رفض التحليل
         */
        confirmReject: async () => {
            const reason = DOM.get('#reject-reason').value.trim();
            if (!reason) {
                Utils.notify(Utils.t('error_reject_requires_reason') || 'يجب إدخال سبب الرفض', 'warning');
                return;
            }

            try {
                const analysisId = Doctor.currentAnalysisId;
                if (!analysisId) throw new Error('Missing analysis id');

                const res = await API.post(`/api/doctor/review/${analysisId}`, {
                    notes: reason, 
                    status: 'rejected'
                });

                if (!res.success) {
                    throw new Error(res.error || Utils.t('error_network'));
                }

                Utils.notify(Utils.t('success_analysis_rejected'), 'success');
                Doctor.closeRejectModal();
                Doctor.loadAnalyses();
            } catch (error) {
                Utils.log('error', 'Error rejecting analysis:', error);
                Utils.notify(error.message || Utils.t('error_network'), 'error');
            }
        },

        /**
         * إرسال تقييم التحليل
         */
        submitReview: async (event, analysisId) => {
            event.preventDefault();
            
            const formData = new FormData(event.target);
            const notes = formData.get('notes');
            const status = 'reviewed'; // Default to approved

            try {
                const res = await API.post(`/api/doctor/review/${analysisId}`, {
                    notes: notes, 
                    status: status
                });

                if (!res.success) {
                    throw new Error(res.error || Utils.t('error_saving_review'));
                }

                Utils.notify(Utils.t('success_review_saved'), 'success');
                event.target.reset();
                Doctor.loadAnalyses();
            } catch (error) {
                Utils.log('error', 'Error submitting review:', error);
                Utils.notify(error.message || Utils.t('error_network'), 'error');
            }
        }
    };

    // ===== Admin Module =====
    const Admin = {
        /**
         * تهيئة صفحة الإدارة
         */
        init: () => {
            // إضافة مستمعي الأحداث
            const themeToggle = DOM.get('#theme-toggle');
            const sidebarToggle = DOM.get('#sidebar-toggle');
            const addUserForm = DOM.get('#add-user-form');
            const settingsForm = DOM.get('#settings-form');
            
            if (themeToggle) {
                themeToggle.addEventListener('click', Theme.toggle);
            }
            
            if (sidebarToggle) {
                sidebarToggle.addEventListener('click', Admin.toggleSidebar);
            }
            
            if (addUserForm) {
                addUserForm.addEventListener('submit', Admin.handleAddUser);
            }
            
            if (settingsForm) {
                settingsForm.addEventListener('submit', Admin.handleSaveSettings);
            }
            
            // تحميل البيانات عند تحميل الصفحة
            Admin.loadDashboardData();
            
            // إضافة مستمعي الأحداث للقائمة الجانبية
            DOM.on('.menu-link', 'click', (e) => {
                e.preventDefault();
                const section = e.currentTarget.getAttribute('data-section');
                Admin.showSection(section);
            });
        },
        
        /**
         * تبديل القائمة الجانبية
         */
        toggleSidebar: () => {
            const sidebar = DOM.get('#sidebar');
            const adminMain = DOM.get('#admin-main');
            const toggleBtn = DOM.get('#sidebar-toggle');
            
            if (!sidebar || !adminMain || !toggleBtn) return;
            
            if (window.innerWidth <= 768) {
                // على الشاشات الصغيرة، إظهار/إخفاء القائمة
                const isOpen = sidebar.classList.contains('open');
                if (isOpen) {
                    sidebar.classList.remove('open');
                    toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
                } else {
                    sidebar.classList.add('open');
                    toggleBtn.innerHTML = '<i class="fas fa-times"></i>';
                }
            } else {
                // على الشاشات الكبيرة، طي/توسيع القائمة
                const isCollapsed = sidebar.classList.contains('collapsed');
                if (isCollapsed) {
                    sidebar.classList.remove('collapsed');
                    adminMain.classList.remove('collapsed');
                    toggleBtn.classList.remove('collapsed');
                    toggleBtn.innerHTML = '<i class="fas fa-chevron-right"></i>';
                } else {
                    sidebar.classList.add('collapsed');
                    adminMain.classList.add('collapsed');
                    toggleBtn.classList.add('collapsed');
                    toggleBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
                }
            }
        },
        
        /**
         * عرض قسم معين
         */
        showSection: (sectionName) => {
            // إخفاء جميع الأقسام
            DOM.hideAll('.page-section');
            
            // إزالة النشط من جميع الروابط
            DOM.removeClassAll('.menu-link', 'active');
            
            // إظهار القسم المطلوب
            DOM.show(`#${sectionName}-section`);
            
            // تفعيل الرابط المطلوب
            DOM.addClass(`.menu-link[data-section="${sectionName}"]`, 'active');
            
            // تحميل البيانات حسب القسم
            if (sectionName === 'dashboard') {
                Admin.loadDashboardData();
            } else if (sectionName === 'users') {
                Admin.loadUsers();
            } else if (sectionName === 'analyses') {
                Admin.loadAnalyses();
            } else if (sectionName === 'settings') {
                Admin.loadSettings();
            }
            
            // إغلاق القائمة على الشاشات الصغيرة
            if (window.innerWidth <= 768) {
                const sidebar = DOM.get('#sidebar');
                const toggleBtn = DOM.get('#sidebar-toggle');
                if (sidebar) sidebar.classList.remove('open');
                if (toggleBtn) toggleBtn.innerHTML = '<i class="fas fa-bars"></i>';
            }
        },
        
        /**
         * تحميل بيانات لوحة التحكم
         */
        loadDashboardData: async () => {
            try {
                const result = await API.get('/admin/stats/system');
                
                if (result.success) {
                    const data = result.data || {};
                    
                    // تحديث الإحصائيات
                    DOM.setText('#total-users', data.total_users || 0);
                    DOM.setText('#total-analyses', data.total_analyses || 0);
                    DOM.setText('#pneumonia-cases', data.pneumonia_cases || 0);
                    
                    // تحريك العدادات
                    Utils.animateCounter('total-users', data.total_users || 0);
                    Utils.animateCounter('total-analyses', data.total_analyses || 0);
                    Utils.animateCounter('pneumonia-cases', data.pneumonia_cases || 0);
                }
            } catch (error) {
                Utils.log('error', 'Error loading dashboard data:', error);
                Utils.notify(Utils.t('error_network'), 'error');
            }
        },
        
        /**
         * تحميل بيانات المستخدمين
         */
        loadUsers: async () => {
            const tbody = DOM.get('#users-table-body');
            if (!tbody) return;
            
            // عرض محملات الهيكل العظمي
            tbody.innerHTML = '';
            for (let i = 0; i < 3; i++) {
                const row = DOM.create('tr');
                row.innerHTML = `<td colspan="5"><div class="skeleton skeleton-row"></div></td>`;
                tbody.appendChild(row);
            }
            
            try {
                const result = await API.get('/admin/stats/users');
                
                if (result.success) {
                    const users = result.data?.items || [];
                    
                    if (users.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="5" class="text-center">${Utils.t('no_data_available')}</td></tr>`;
                        return;
                    }
                    
                    tbody.innerHTML = users.map(user => `
                        <tr>
                            <td>${user.username}</td>
                            <td>${user.email}</td>
                            <td><span class="badge badge-${user.role}">${Admin.getRoleName(user.role)}</span></td>
                            <td><span class="badge ${user.is_active ? 'badge-active' : 'badge-inactive'}">${user.is_active ? Utils.t('status_active') : Utils.t('status_inactive')}</span></td>
                            <td>
                                <div class="action-buttons">
                                    <button class="btn btn-edit" onclick="Admin.editUser('${user.id}')" aria-label="${Utils.t('edit_user')} ${user.username}"><i class="fas fa-edit"></i></button>
                                    <button class="btn btn-delete" onclick="Admin.deleteUser('${user.id}')" aria-label="${Utils.t('delete_user')} ${user.username}"><i class="fas fa-trash"></i></button>
                                </div>
                            </td>
                        </tr>
                    `).join('');
                }
            } catch (error) {
                Utils.log('error', 'Error loading users:', error);
                Utils.notify(Utils.t('error_network'), 'error');
                tbody.innerHTML = `<tr><td colspan="5" class="error-message">${Utils.t('error_network')}</td></tr>`;
            }
        },
        
        /**
         * تحميل بيانات التحاليل
         */
        loadAnalyses: async () => {
            const tbody = DOM.get('#analyses-table-body');
            if (!tbody) return;
            
            // عرض محملات الهيكل العظمي
            tbody.innerHTML = '';
            for (let i = 0; i < 2; i++) {
                const row = DOM.create('tr');
                row.innerHTML = `<td colspan="6"><div class="skeleton skeleton-row"></div></td>`;
                tbody.appendChild(row);
            }
            
            try {
                const result = await API.get('/admin/analyses');
                
                if (result.success) {
                    const analyses = result.data?.items || [];
                    
                    if (analyses.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="6" class="text-center">${Utils.t('no_data_available')}</td></tr>`;
                        return;
                    }
                    
                    tbody.innerHTML = analyses.map(analysis => `
                        <tr>
                            <td>${analysis.id}</td>
                            <td>${analysis.patient_name}</td>
                            <td>${analysis.doctor_name}</td>
                            <td>${Utils.formatDate(analysis.date)}</td>
                            <td><span class="badge ${analysis.result === 'pneumonia' ? 'badge-danger' : 'badge-success'}">${analysis.result}</span></td>
                            <td><span class="badge ${analysis.status === 'completed' ? 'badge-success' : 'badge-warning'}">${analysis.status}</span></td>
                        </tr>
                    `).join('');
                }
            } catch (error) {
                Utils.log('error', 'Error loading analyses:', error);
                Utils.notify(Utils.t('error_network'), 'error');
                tbody.innerHTML = `<tr><td colspan="6" class="error-message">${Utils.t('error_network')}</td></tr>`;
            }
        },
        
        /**
         * تحميل الإعدادات
         */
        loadSettings: async () => {
            try {
                const result = await API.get('/admin/settings');
                
                if (result.success) {
                    const settings = result.data || {};
                    
                    // تحديث حقول الإعدادات
                    DOM.get('#max-file-size').value = settings.max_file_size || 50;
                    DOM.get('#daily-limit').value = settings.daily_limit || 100;
                    DOM.get('#min-confidence').value = settings.min_confidence || 70;
                }
            } catch (error) {
                Utils.log('error', 'Error loading settings:', error);
                Utils.notify(Utils.t('error_network'), 'error');
            }
        },
        
        /**
         * معالجة إضافة مستخدم جديد
         */
        handleAddUser: async (e) => {
            e.preventDefault();
            
            // التحقق من صحة النموذج
            if (!Forms.validateAddUserForm('#add-user-form')) {
                Utils.notify(Utils.t('error_form_validation'), 'error');
                return;
            }
            
            // الحصول على بيانات النموذج
            const formData = Forms.getFormData('#add-user-form');
            
            try {
                const result = await API.post('/admin/users', formData);
                
                if (result.success) {
                    Utils.notify(Utils.t('success_user_added'), 'success');
                    e.target.reset();
                    Admin.loadUsers();
                } else {
                    Utils.notify(result.error || Utils.t('error_adding_user'), 'error');
                }
            } catch (error) {
                Utils.log('error', 'Error adding user:', error);
                Utils.notify(Utils.t('error_network'), 'error');
            }
        },
        
        /**
         * معالجة حفظ الإعدادات
         */
        handleSaveSettings: async (e) => {
            e.preventDefault();
            
            // الحصول على بيانات النموذج
            const formData = Forms.getFormData('#settings-form');
            
            try {
                const result = await API.post('/admin/settings', formData);
                
                if (result.success) {
                    Utils.notify(Utils.t('success_settings_saved'), 'success');
                } else {
                    Utils.notify(result.error || Utils.t('error_saving_settings'), 'error');
                }
            } catch (error) {
                Utils.log('error', 'Error saving settings:', error);
                Utils.notify(Utils.t('error_network'), 'error');
            }
        },
        
        /**
         * تعديل مستخدم
         */
        editUser: (userId) => {
            Utils.notify(`${Utils.t('edit_user')} ${userId} (${Utils.t('simulation')})`, 'info');
        },
        
        /**
         * حذف مستخدم
         */
        deleteUser: (userId) => {
            Admin.openModal(
                Utils.t('confirm_delete_user'),
                async () => {
                    try {
                        const result = await API.put(`/admin/users/${userId}/status`, { is_active: false });
                        
                        if (result.success) {
                            Utils.notify(Utils.t('success_user_deleted'), 'success');
                            Admin.loadUsers();
                        } else {
                            Utils.notify(result.error || Utils.t('error_network'), 'error');
                        }
                    } catch (error) {
                        Utils.log('error', 'Error deleting user:', error);
                        Utils.notify(Utils.t('error_network'), 'error');
                    }
                }
            );
        },
        
        /**
         * فتح نافذة منبثقة للتأكيد
         */
        openModal: (message, onConfirm) => {
            const modal = DOM.get('#confirm-modal');
            const messageEl = DOM.get('#modal-message');
            const confirmBtn = DOM.get('#confirm-btn');
            
            if (!modal || !messageEl || !confirmBtn) return;
            
            messageEl.textContent = message;
            confirmBtn.onclick = () => {
                onConfirm();
                Admin.closeModal();
            };
            
            modal.style.display = 'block';
            modal.setAttribute('aria-hidden', 'false');
            
            // التركيز على زر التأكيد
            setTimeout(() => {
                confirmBtn.focus();
            }, 100);
        },
        
        /**
         * إغلاق النافذة المنبثقة
         */
        closeModal: () => {
            const modal = DOM.get('#confirm-modal');
            if (!modal) return;
            
            modal.style.display = 'none';
            modal.setAttribute('aria-hidden', 'true');
        },
        
        /**
         * الحصول على اسم الدور
         */
        getRoleName: (role) => {
            const roles = {
                patient: Utils.t('role_patient'),
                doctor: Utils.t('role_doctor'),
                admin: Utils.t('role_admin')
            };
            return roles[role] || role;
        },
        
        /**
         * تسجيل الخروج
         */
        logout: () => {
            Admin.openModal(
                Utils.t('confirm_logout'),
                () => {
                    // في تطبيق حقيقي، هذا سيمسح الجلسة ويعيد توجيه إلى صفحة تسجيل الدخول
                    localStorage.removeItem('pneumoDetectToken');
                    window.location.href = '/login';
                }
            );
        }
    };

    // ===== UI Helpers Module =====
    const UI = {
        /**
         * تحسين تحميل الصور تدريجياً (lazy + blur-up)
         */
        initProgressiveImages: () => {
            try {
                // Apply native lazy loading and a progressive blur-up effect
                document.querySelectorAll('img').forEach(img => {
                    // skip icons and data URIs
                    if (img.dataset.noprogressive) return;
                    if (!img.hasAttribute('loading')) img.setAttribute('loading', 'lazy');
                    img.classList.add('progressive-img');
                    // If image has data-src (rendered by templates), keep placeholder blurred
                    const dataSrc = img.getAttribute('data-src') || img.dataset.src;
                    if (dataSrc) {
                        // keep placeholder blurred until the real image loads
                        img.style.filter = 'blur(6px)';
                        img.style.transition = 'filter 400ms ease, opacity 300ms ease';
                        img.addEventListener('load', () => {
                            img.style.filter = 'none';
                        }, { once: true });
                    } else {
                        // For images without data-src, ensure we remove any temporary blur on load
                        const src = img.getAttribute('src');
                        if (src && src.indexOf('data:') !== 0) {
                            img.style.transition = 'filter 400ms ease, opacity 300ms ease';
                            img.addEventListener('load', () => {
                                img.style.filter = 'none';
                            }, { once: true });
                        }
                    }
                });

                // IntersectionObserver to load images that have data-src attribute
                if ('IntersectionObserver' in window) {
                    const io = new IntersectionObserver((entries) => {
                        entries.forEach(entry => {
                            if (!entry.isIntersecting) return;
                            const img = entry.target;
                            const dataSrc = img.getAttribute('data-src');
                            if (dataSrc) {
                                img.src = dataSrc;
                                img.removeAttribute('data-src');
                            }
                            io.unobserve(img);
                        });
                    }, { rootMargin: '200px' });

                    document.querySelectorAll('img[data-src]').forEach(img => io.observe(img));

                    // Observe DOM mutations and start observing any newly added images with data-src
                    if ('MutationObserver' in window) {
                        try {
                            const mo = new MutationObserver((mutations) => {
                                mutations.forEach(m => {
                                    if (!m.addedNodes) return;
                                    m.addedNodes.forEach(node => {
                                        try {
                                            if (!node) return;
                                            if (node.nodeType === 1) {
                                                // If an IMG node with data-src was added
                                                if (node.tagName === 'IMG' && node.getAttribute('data-src')) {
                                                    io.observe(node);
                                                } else {
                                                    // If a subtree was added, observe any imgs inside it
                                                    const imgs = node.querySelectorAll && node.querySelectorAll('img[data-src]');
                                                    if (imgs && imgs.length) imgs.forEach(i => io.observe(i));
                                                }
                                            }
                                        } catch(_e){}
                                    });
                                });
                            });
                            mo.observe(document.body, { childList: true, subtree: true });
                        } catch(e) { /* ignore */ }
                    }
                }
            } catch (e) {
                Utils.log('error', 'Progressive images init failed', e);
            }
        },

        /**
         * Print integration: adds handler to `#print-btn` and a programmatic print helper
         */
        initPrintButton: () => {
            try {
                const btn = document.getElementById('print-btn');
                if (btn) {
                    btn.addEventListener('click', (e) => {
                        e.preventDefault();
                        // Minor UX: hide interactive elements then print
                        document.documentElement.classList.add('printing');
                        setTimeout(() => {
                            window.print();
                            setTimeout(() => document.documentElement.classList.remove('printing'), 500);
                        }, 50);
                    });
                }
            } catch (e) {
                Utils.log('error', 'Print button init failed', e);
            }
        },

        /**
         * Device tester overlay for quick device diagnostics (activated via ?dev=1 or Ctrl+Shift+D)
         */
        initDeviceTester: () => {
            try {
                const showOverlay = () => {
                    if (document.getElementById('device-tester-overlay')) return;
                    const overlay = document.createElement('div');
                    overlay.id = 'device-tester-overlay';
                    overlay.innerHTML = `
                        <div class="dt-card">
                            <h4>Device Test Report</h4>
                            <pre id="dt-report"></pre>
                            <div class="dt-actions">
                                <button id="dt-copy" class="btn btn-secondary">Copy</button>
                                <button id="dt-close" class="btn btn-primary">Close</button>
                            </div>
                        </div>`;
                    document.body.appendChild(overlay);

                    const reportEl = document.getElementById('dt-report');
                    const info = {
                        url: window.location.href,
                        width: window.innerWidth,
                        height: window.innerHeight,
                        devicePixelRatio: window.devicePixelRatio || 1,
                        userAgent: navigator.userAgent,
                        language: navigator.language || document.documentElement.lang || '',
                        timestamp: new Date().toISOString()
                    };
                    reportEl.textContent = JSON.stringify(info, null, 2);

                    document.getElementById('dt-copy').addEventListener('click', async () => {
                        try { await navigator.clipboard.writeText(reportEl.textContent); Utils.notify('Device report copied to clipboard', 'success'); } catch(e){ Utils.notify('Copy failed', 'warning'); }
                    });
                    document.getElementById('dt-close').addEventListener('click', () => overlay.remove());
                };

                // Auto open if ?dev=1
                const params = new URLSearchParams(window.location.search);
                if (params.get('dev') === '1') showOverlay();

                // Key combo Ctrl+Shift+D to toggle
                window.addEventListener('keydown', (e) => {
                    if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'd') {
                        showOverlay();
                    }
                });
            } catch (e) {
                Utils.log('error', 'Device tester init failed', e);
            }
        }
    };

    // ===== Public API =====
    return {
        Utils,
        API,
        DOM,
        Theme,
        Language,
        Forms,
        Auth,
        Login,
        Patient,
        Doctor,
        Admin,
        Index,
        state,
        CONFIG,
        UI,
        
        /**
         * تهيئة التطبيق
         */
        init: (config = {}) => {
            Object.assign(CONFIG, config);
            Theme.init();
            Language.init();
            
            // الحصول على CSRF Token
            const csrfMeta = document.querySelector('meta[name="csrf-token"]');
            if (csrfMeta) {
                state.csrfToken = csrfMeta.getAttribute('content');
            }

            Utils.log('info', 'PneumoApp initialized', CONFIG);
            
            // تشغيل أي دوال تهيئة مخصصة
            if (window.onAppInit) {
                window.onAppInit();
            }
        }
    };
})();

// تهيئة التطبيق عند تحميل الـ DOM
document.addEventListener('DOMContentLoaded', () => {
    PneumoApp.init();
    // Initialize UI helpers (progressive images, print button, device tester)
    if (PneumoApp.UI) {
        PneumoApp.UI.initProgressiveImages();
        PneumoApp.UI.initPrintButton();
        PneumoApp.UI.initDeviceTester();
    }
    
    // تهيئة صفحة تسجيل الدخول إذا كانت الصفحة الحالية هي صفحة تسجيل الدخول
    if (document.getElementById('login-form')) {
        PneumoApp.Login.init();
    }
    
    // تهيئة صفحة المريض إذا كانت الصفحة الحالية هي صفحة المريض
    if (document.getElementById('results-list')) {
        PneumoApp.Patient.init();
    }
    
    // تهيئة صفحة الطبيب إذا كانت الصفحة الحالية هي صفحة الطبيب
    if (document.getElementById('analyses-list')) {
        PneumoApp.Doctor.init();
    }
    
    // تهيئة صفحة الإدارة إذا كانت الصفحة الحالية هي صفحة الإدارة
    if (document.getElementById('admin-main')) {
        PneumoApp.Admin.init();
    }
    
    // تهيئة صفحة الرئيسية
    if (document.getElementById('home-section')) {
        PneumoApp.Index.init();
    }
});