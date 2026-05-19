// ============================================
// Prizolov Sports AI - Live Recommendations Widget
// Version: 1.01 (+1.01: Production WebSocket Integration & Dynamic DOM Rendering)
// Author: Dm.Andreyanov
// Organization: Prizolov Market / Prizolov Lab
// Target: Integration at prizolov.ru/sport/
// ============================================

(function (window, document) {
    'use strict';

    const CONFIG = {
        containerSelector: '[data-prizolov-feed]',
        maxItems: 12,
        reconnectBaseDelay: 1000,
        maxReconnectDelay: 15000,
        statusClass: {
            connecting: 'pz-live-connecting',
            connected: 'pz-live-connected',
            disconnected: 'pz-live-disconnected',
            error: 'pz-live-error'
        }
    };

    class PrizolovLiveFeed {
        constructor(container) {
            this.container = container;
            this.wsUrl = container.dataset.wsUrl || this._detectWsUrl();
            this.ws = null;
            this.reconnectTimer = null;
            this.reconnectAttempts = 0;
            this.itemsCache = new Map();
            
            this._initStyles();
            this._renderStructure();
            this.connect();
        }

        _detectWsUrl() {
            const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
            const host = window.location.hostname;
            const port = window.location.port || '8080';
            return `${protocol}${host}:${port}`;
        }

        _initStyles() {
            if (document.getElementById('pz-live-styles')) return;
            const style = document.createElement('style');
            style.id = 'pz-live-styles';
            style.textContent = `
                .pz-feed-container { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; }
                .pz-header { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee; }
                .pz-status-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
                .pz-status-dot.pz-live-connecting { background: #f59e0b; animation: pz-pulse 1.5s infinite; }
                .pz-status-dot.pz-live-connected { background: #10b981; }
                .pz-status-dot.pz-live-disconnected, .pz-status-dot.pz-live-error { background: #ef4444; }
                @keyframes pz-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
                .pz-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
                .pz-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; box-shadow: 0 1px 2px rgba(0,0,0,0.05); transition: transform 0.2s, box-shadow 0.2s; }
                .pz-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px rgba(0,0,0,0.08); }
                .pz-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
                .pz-match-id { font-size: 0.75rem; color: #6b7280; font-weight: 500; }
                .pz-time { font-size: 0.7rem; color: #9ca3af; }
                .pz-line { font-size: 1.1rem; font-weight: 600; color: #111827; margin-bottom: 4px; }
                .pz-stats { display: flex; gap: 12px; margin-top: 8px; }
                .pz-stat { font-size: 0.8rem; color: #4b5563; }
                .pz-stat strong { color: #059669; }
                .pz-empty { text-align: center; padding: 30px 10px; color: #6b7280; background: #f9fafb; border-radius: 8px; border: 1px dashed #d1d5db; }
            `;
            document.head.appendChild(style);
        }

        _renderStructure() {
            this.container.innerHTML = `
                <div class="pz-feed-container">
                    <div class="pz-header">
                        <span class="pz-status-dot ${CONFIG.statusClass.connecting}"></span>
                        <span class="pz-title" style="font-weight:600; font-size:1.1rem;">Рекомендации AI (Live)</span>
                    </div>
                    <div class="pz-grid" id="pz-grid"></div>
                    <div class="pz-empty" id="pz-empty" style="display:none;">Нет доступных линий с коэф. ≥ 1.60 на данный момент</div>
                </div>
            `;
            this.grid = this.container.querySelector('#pz-grid');
            this.emptyState = this.container.querySelector('#pz-empty');
            this.statusDot = this.container.querySelector('.pz-status-dot');
        }

        _setStatus(status) {
            this.statusDot.className = `pz-status-dot ${CONFIG.statusClass[status] || CONFIG.statusClass.disconnected}`;
        }

        connect() {
            if (this.ws) this.ws.close();
            this._setStatus('connecting');

            try {
                this.ws = new WebSocket(this.wsUrl);
                this.ws.onopen = () => {
                    this._setStatus('connected');
                    this.reconnectAttempts = 0;
                    console.log('[PrizolovLive] WebSocket connected');
                    this.ws.send(JSON.stringify({ action: 'get_state' }));
                };
                this.ws.onmessage = (e) => this._handleMessage(e.data);
                this.ws.onclose = () => this._scheduleReconnect();
                this.ws.onerror = () => {
                    this._setStatus('error');
                    console.warn('[PrizolovLive] WebSocket error');
                };
            } catch (err) {
                console.error('[PrizolovLive] Connection failed:', err);
                this._scheduleReconnect();
            }
        }

        _handleMessage(raw) {
            try {
                const data = JSON.parse(raw);
                if (data.status === 'pong') return;
                if (data.recommendations && Array.isArray(data.recommendations)) {
                    this._renderData(data.recommendations);
                }
            } catch (e) {
                console.warn('[PrizolovLive] Invalid message format:', e);
            }
        }

        _renderData(rawItems) {
            // Фильтрация и сортировка на фронтенде (дополнительная защита)
            const filtered = rawItems
                .filter(item => item.coefficient >= 1.60 && item.line)
                .sort((a, b) => b.probability - a.probability)
                .slice(0, CONFIG.maxItems);

            // Обновляем кэш и удаляем устаревшие (>5 мин)
            const now = Date.now();
            filtered.forEach(item => this.itemsCache.set(item.match_id, { ...item, ts: now }));
            for (const [id, data] of this.itemsCache) {
                if (now - data.ts > 300000) this.itemsCache.delete(id);
            }

            // Рендеринг
            this.grid.innerHTML = '';
            if (this.itemsCache.size === 0) {
                this.emptyState.style.display = 'block';
                return;
            }
            this.emptyState.style.display = 'none';

            this.itemsCache.forEach(item => {
                const card = document.createElement('div');
                card.className = 'pz-card';
                card.innerHTML = `
                    <div class="pz-card-header">
                        <span class="pz-match-id">ID: ${item.match_id.substring(0, 8)}...</span>
                        <span class="pz-time">${item.game_time || ''}</span>
                    </div>
                    <div class="pz-line">${item.line} @ <span style="color:#059669;">${item.coefficient}</span></div>
                    <div class="pz-stats">
                        <span class="pz-stat">Вероятность: <strong>${Math.round(item.probability * 100)}%</strong></span>
                        <span class="pz-stat">Уверенность: <strong>${this._translateConf(item.confidence)}</strong></span>
                    </div>
                `;
                this.grid.appendChild(card);
            });
        }

        _translateConf(conf) {
            const map = { high: 'Высокая', medium: 'Средняя', low: 'Низкая' };
            return map[conf] || conf;
        }

        _scheduleReconnect() {
            if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
            const delay = Math.min(
                CONFIG.reconnectBaseDelay * Math.pow(1.5, this.reconnectAttempts),
                CONFIG.maxReconnectDelay
            );
            this._setStatus('disconnected');
            console.log(`[PrizolovLive] Reconnecting in ${Math.round(delay/1000)}s...`);
            this.reconnectTimer = setTimeout(() => {
                this.reconnectAttempts++;
                this.connect();
            }, delay);
        }

        destroy() {
            if (this.ws) this.ws.close();
            if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
        }
    }

    // Автоинициализация при загрузке DOM
    function initAll() {
        document.querySelectorAll(CONFIG.containerSelector).forEach(el => new PrizolovLiveFeed(el));
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAll);
    } else {
        initAll();
    }

    // Экспорт для ручного управления (опционально)
    window.PrizolovLiveFeed = PrizolovLiveFeed;
})(window, document);
