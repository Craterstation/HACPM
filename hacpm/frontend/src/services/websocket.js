/**
 * HACPM WebSocket Client
 * Provides real-time sync for task updates.
 */

class HacpmWebSocket {
  constructor() {
    this._ws = null;
    this._listeners = new Map();
    this._reconnectDelay = 1000;
    this._maxReconnectDelay = 30000;
    this._pingInterval = null;
    this._userId = null;
  }

  connect(userId = null) {
    this._userId = userId;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    let url = `${protocol}//${window.location.host}${window.location.pathname}`;
    // Ensure trailing slash for path join
    if (!url.endsWith('/')) url += '/';
    url = url.replace(/\/+$/, '') + '/ws';
    if (userId) url += `?user_id=${userId}`;

    try {
      this._ws = new WebSocket(url);
    } catch {
      this._scheduleReconnect();
      return;
    }

    this._ws.onopen = () => {
      console.log('[HACPM WS] Connected');
      this._reconnectDelay = 1000;
      // Start ping to keep alive
      this._pingInterval = setInterval(() => {
        if (this._ws?.readyState === WebSocket.OPEN) {
          this._ws.send('ping');
        }
      }, 30000);
    };

    this._ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (message.event === 'pong') return;
        this._dispatch(message.event, message.data);
      } catch {
        // ignore non-JSON messages
      }
    };

    this._ws.onclose = () => {
      console.log('[HACPM WS] Disconnected');
      clearInterval(this._pingInterval);
      this._scheduleReconnect();
    };

    this._ws.onerror = () => {
      this._ws?.close();
    };
  }

  disconnect() {
    clearInterval(this._pingInterval);
    if (this._ws) {
      this._ws.onclose = null; // Prevent reconnect
      this._ws.close();
      this._ws = null;
    }
  }

  on(event, callback) {
    if (!this._listeners.has(event)) {
      this._listeners.set(event, new Set());
    }
    this._listeners.get(event).add(callback);
    return () => this._listeners.get(event)?.delete(callback);
  }

  _dispatch(event, data) {
    const handlers = this._listeners.get(event);
    if (handlers) {
      handlers.forEach(cb => cb(data));
    }
    // Also dispatch a wildcard for components that listen to all events
    const wildcardHandlers = this._listeners.get('*');
    if (wildcardHandlers) {
      wildcardHandlers.forEach(cb => cb(event, data));
    }
  }

  _scheduleReconnect() {
    setTimeout(() => {
      console.log(`[HACPM WS] Reconnecting in ${this._reconnectDelay}ms...`);
      this.connect(this._userId);
      this._reconnectDelay = Math.min(this._reconnectDelay * 2, this._maxReconnectDelay);
    }, this._reconnectDelay);
  }
}

export const ws = new HacpmWebSocket();
