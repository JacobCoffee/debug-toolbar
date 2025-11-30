/**
 * Debug Toolbar Examples - Shared JavaScript
 */

// Namespace for shared utilities
window.DebugToolbarExamples = window.DebugToolbarExamples || {};

(function(DTE) {
    'use strict';

    /**
     * Theme Management
     */
    DTE.Theme = {
        STORAGE_KEY: 'debug-toolbar-theme',

        init: function() {
            // Check for saved preference or system preference
            const saved = localStorage.getItem(this.STORAGE_KEY);
            if (saved) {
                this.set(saved);
            }
            // System preference is handled by CSS @media query
        },

        get: function() {
            return document.documentElement.getAttribute('data-theme') ||
                   (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
        },

        set: function(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem(this.STORAGE_KEY, theme);
            this.updateToggleButton();
        },

        toggle: function() {
            const current = this.get();
            this.set(current === 'dark' ? 'light' : 'dark');
        },

        updateToggleButton: function() {
            const btn = document.getElementById('theme-toggle');
            if (btn) {
                const icon = btn.querySelector('.icon');
                const text = btn.querySelector('.text');
                const isDark = this.get() === 'dark';
                if (icon) icon.textContent = isDark ? '☀️' : '🌙';
                if (text) text.textContent = isDark ? 'Light' : 'Dark';
            }
        },

        createToggleButton: function() {
            const btn = document.createElement('button');
            btn.id = 'theme-toggle';
            btn.className = 'theme-toggle';
            btn.innerHTML = '<span class="icon">🌙</span><span class="text">Dark</span>';
            btn.onclick = () => this.toggle();
            document.body.appendChild(btn);
            this.updateToggleButton();
        }
    };

    /**
     * Format bytes to human readable string
     * @param {number} bytes - Number of bytes
     * @param {number} decimals - Decimal places (default: 2)
     * @returns {string} Formatted string like "1.5 KB"
     */
    DTE.formatBytes = function(bytes, decimals = 2) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
    };

    /**
     * Format duration in milliseconds to human readable
     * @param {number} ms - Duration in milliseconds
     * @returns {string} Formatted string like "1.5s" or "150ms"
     */
    DTE.formatDuration = function(ms) {
        if (ms < 1) return '<1ms';
        if (ms < 1000) return Math.round(ms) + 'ms';
        if (ms < 60000) return (ms / 1000).toFixed(1) + 's';
        const minutes = Math.floor(ms / 60000);
        const seconds = Math.round((ms % 60000) / 1000);
        return minutes + 'm ' + seconds + 's';
    };

    /**
     * Format timestamp to local time string
     * @param {number|Date} timestamp - Unix timestamp (ms) or Date object
     * @returns {string} Formatted time string
     */
    DTE.formatTime = function(timestamp) {
        const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    /**
     * Create and append a message element to a container
     * @param {string} containerId - ID of the container element
     * @param {string} text - Message text
     * @param {string} type - Message type: 'sent', 'received', or 'system'
     */
    DTE.addMessage = function(containerId, text, type) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const div = document.createElement('div');
        div.className = 'message message-' + type;

        const time = document.createElement('span');
        time.className = 'message-time';
        time.textContent = DTE.formatTime(new Date()) + ' ';

        div.appendChild(time);
        div.appendChild(document.createTextNode(text));

        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    };

    /**
     * Update connection status display
     * @param {string} prefix - Element ID prefix (e.g., 'echo' for 'echo-status')
     * @param {boolean} connected - Whether connected
     */
    DTE.updateStatus = function(prefix, connected) {
        const status = document.getElementById(prefix + '-status');
        if (status) {
            status.textContent = connected ? 'Connected' : 'Disconnected';
            status.className = 'status ' + (connected ? 'status-connected' : 'status-disconnected');
        }

        // Enable/disable related controls
        const input = document.getElementById(prefix + '-input');
        const sendBtn = document.getElementById(prefix + '-send');
        const connectBtn = document.getElementById(prefix + '-connect');
        const disconnectBtn = document.getElementById(prefix + '-disconnect');

        if (input) input.disabled = !connected;
        if (sendBtn) sendBtn.disabled = !connected;
        if (connectBtn) connectBtn.disabled = connected;
        if (disconnectBtn) disconnectBtn.disabled = !connected;
    };

    /**
     * WebSocket connection manager
     */
    DTE.WebSocketManager = class {
        constructor(options) {
            this.prefix = options.prefix;
            this.url = options.url;
            this.onMessage = options.onMessage || function() {};
            this.onOpen = options.onOpen || function() {};
            this.onClose = options.onClose || function() {};
            this.onError = options.onError || function() {};
            this.ws = null;
        }

        connect() {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                return;
            }

            const wsUrl = this.url.startsWith('ws')
                ? this.url
                : 'ws://' + window.location.host + this.url;

            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                DTE.updateStatus(this.prefix, true);
                DTE.addMessage(this.prefix + '-messages', 'Connected', 'system');
                this.onOpen();
            };

            this.ws.onmessage = (event) => {
                this.onMessage(event.data);
            };

            this.ws.onclose = (event) => {
                DTE.updateStatus(this.prefix, false);
                DTE.addMessage(
                    this.prefix + '-messages',
                    'Disconnected (code: ' + event.code + ')',
                    'system'
                );
                this.onClose(event);
            };

            this.ws.onerror = (error) => {
                DTE.addMessage(this.prefix + '-messages', 'Connection error', 'system');
                this.onError(error);
            };
        }

        disconnect(code = 1000, reason = 'User disconnect') {
            if (this.ws) {
                this.ws.close(code, reason);
            }
        }

        send(data) {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(data);
                return true;
            }
            return false;
        }

        isConnected() {
            return this.ws && this.ws.readyState === WebSocket.OPEN;
        }
    };

    /**
     * Debounce function execution
     * @param {Function} func - Function to debounce
     * @param {number} wait - Wait time in ms
     * @returns {Function} Debounced function
     */
    DTE.debounce = function(func, wait) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(this, args), wait);
        };
    };

    /**
     * Escape HTML to prevent XSS
     * @param {string} str - String to escape
     * @returns {string} Escaped string
     */
    DTE.escapeHtml = function(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    };

    /**
     * Copy text to clipboard
     * @param {string} text - Text to copy
     * @returns {Promise<boolean>} Success status
     */
    DTE.copyToClipboard = async function(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            console.error('Failed to copy:', err);
            return false;
        }
    };

    /**
     * Show a toast notification
     * @param {string} message - Message to display
     * @param {string} type - Type: 'success', 'error', 'info', 'warning'
     * @param {number} duration - Duration in ms (default: 3000)
     */
    DTE.toast = function(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 24px;
            border-radius: 4px;
            color: white;
            font-size: 14px;
            z-index: 10000;
            animation: fadeIn 0.3s ease;
        `;

        const colors = {
            success: '#10b981',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#3b82f6'
        };
        toast.style.backgroundColor = colors[type] || colors.info;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    };

    /**
     * Initialize enter key handler for input fields
     * @param {string} inputId - Input element ID
     * @param {Function} callback - Function to call on enter
     */
    DTE.onEnter = function(inputId, callback) {
        const input = document.getElementById(inputId);
        if (input) {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    callback();
                }
            });
        }
    };

    /**
     * Simple JSON syntax highlighting
     * @param {object|string} json - JSON object or string
     * @returns {string} HTML with highlighted JSON
     */
    DTE.highlightJson = function(json) {
        const str = typeof json === 'string' ? json : JSON.stringify(json, null, 2);
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"([^"]+)":/g, '<span style="color:#7c3aed">"$1"</span>:')
            .replace(/: "([^"]*)"/g, ': <span style="color:#059669">"$1"</span>')
            .replace(/: (\d+)/g, ': <span style="color:#d97706">$1</span>')
            .replace(/: (true|false|null)/g, ': <span style="color:#0ea5e9">$1</span>');
    };

    // Add CSS for toast animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeOut {
            from { opacity: 1; transform: translateY(0); }
            to { opacity: 0; transform: translateY(20px); }
        }
    `;
    document.head.appendChild(style);

    // Log initialization
    console.log('Debug Toolbar Examples JS loaded');

})(window.DebugToolbarExamples);
