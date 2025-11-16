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
        csrfToken: null
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
         * إظهار إشعار للمستخدم
         */
        notify: (message, type = 'info', duration = 4000) => {
            const notification = {
                id: Date.now(),
                message,
                type, // info, success, warning, error
                duration
            };
            
            state.notifications.push(notification);
            
            // إنشاء عنصر الإشعار
            const el = document.createElement('div');
            el.className = `notification notification-${type}`;
            el.textContent = message;
            el.setAttribute('role', 'alert');
            
            // إضافة إلى الصفحة
            const container = document.querySelector('[role="alert-container"]') || 
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
                        'X-CSRF-Token': state.csrfToken || ''
                    },
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
                Utils.notify(`خطأ: ${error.message}`, 'error');
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

    // ===== Forms Module =====
    const Forms = {
        /**
         * التحقق من صحة نموذج
         */
        validate: (formSelector) => {
            const form = DOM.get(formSelector);
            if (!form) return false;

            const inputs = form.querySelectorAll('input, textarea, select');
            let isValid = true;

            inputs.forEach(input => {
                if (!Forms.validateField(input)) {
                    isValid = false;
                }
            });

            return isValid;
        },

        /**
         * التحقق من حقل واحد
         */
        validateField: (field) => {
            const value = field.value.trim();
            const type = field.type;
            const required = field.hasAttribute('required');

            if (required && !value) {
                Forms.setError(field, 'هذا الحقل مطلوب');
                return false;
            }

            if (type === 'email' && value && !Utils.isValidEmail(value)) {
                Forms.setError(field, 'البريد الإلكتروني غير صحيح');
                return false;
            }

            if (type === 'password' && value && value.length < 6) {
                Forms.setError(field, 'كلمة المرور يجب أن تكون 6 أحرف على الأقل');
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
            
            if (!errorEl || !errorEl.classList.contains('error-message')) {
                errorEl = DOM.create('small', 'error-message', message);
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
            if (errorEl && errorEl.classList.contains('error-message')) {
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
        }
    };

    // ===== Auth Module =====
    const Auth = {
        /**
         * الحصول على بيانات المستخدم الحالي
         */
        getCurrentUser: () => state.user,

        /**
         * تسجيل الدخول
         */
        login: async (email, password) => {
            const result = await API.post('/auth/login', { email, password });
            if (result.success) {
                state.user = result.data.user;
                Utils.notify('تم تسجيل الدخول بنجاح', 'success');
                return true;
            }
            return false;
        },

        /**
         * تسجيل الخروج
         */
        logout: async () => {
            const result = await API.post('/auth/logout');
            if (result.success) {
                state.user = null;
                Utils.notify('تم تسجيل الخروج', 'info');
                return true;
            }
            return false;
        },

        /**
         * التحقق من أن المستخدم مسجل دخول
         */
        isAuthenticated: () => state.user !== null
    };

    // ===== Public API =====
    return {
        Utils,
        API,
        DOM,
        Theme,
        Forms,
        Auth,
        state,
        CONFIG,
        
        /**
         * تهيئة التطبيق
         */
        init: (config = {}) => {
            Object.assign(CONFIG, config);
            Theme.init();
            
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
});
