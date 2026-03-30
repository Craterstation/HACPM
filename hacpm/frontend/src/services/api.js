/**
 * HACPM API Client
 * Handles all HTTP communication with the FastAPI backend.
 */

class HacpmApi {
  constructor() {
    // Detect ingress base path from current page URL
    // HA ingress URLs look like: /api/hassio_ingress/TOKEN_HERE/
    // We need to prefix all API calls with this path
    let base = window.location.pathname;
    // Remove trailing slash and any filename
    base = base.replace(/\/+$/, '');
    this.baseUrl = base;
  }

  async _fetch(path, options = {}) {
    const url = `${this.baseUrl}/api${path}`;
    const defaults = {
      headers: { 'Content-Type': 'application/json' },
    };
    const config = { ...defaults, ...options };
    if (config.body && typeof config.body === 'object' && !(config.body instanceof FormData)) {
      config.body = JSON.stringify(config.body);
    }
    if (config.body instanceof FormData) {
      delete config.headers['Content-Type'];
    }
    const response = await fetch(url, config);
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: response.statusText }));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }
    if (response.status === 204) return null;
    return response.json();
  }

  // ── Users ──
  getUsers(activeOnly = true) {
    return this._fetch(`/users/?active_only=${activeOnly}`);
  }
  getUser(id) {
    return this._fetch(`/users/${id}`);
  }
  createUser(data) {
    return this._fetch('/users/', { method: 'POST', body: data });
  }
  updateUser(id, data) {
    return this._fetch(`/users/${id}`, { method: 'PUT', body: data });
  }
  deleteUser(id) {
    return this._fetch(`/users/${id}`, { method: 'DELETE' });
  }
  verifyPin(userId, pin) {
    return this._fetch(`/users/${userId}/verify-pin?pin=${encodeURIComponent(pin)}`, { method: 'POST' });
  }

  // ── Tasks ──
  getTasks({ status, assigneeId, labelId, parentOnly } = {}) {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (assigneeId) params.set('assignee_id', assigneeId);
    if (labelId) params.set('label_id', labelId);
    if (parentOnly !== undefined) params.set('parent_only', parentOnly);
    return this._fetch(`/tasks/?${params}`);
  }
  getTask(id) {
    return this._fetch(`/tasks/${id}`);
  }
  createTask(data) {
    return this._fetch('/tasks/', { method: 'POST', body: data });
  }
  createTaskFromNLP(text, createdBy = null, assigneeIds = [], labelIds = []) {
    return this._fetch('/tasks/nlp', {
      method: 'POST',
      body: { text, created_by: createdBy, assignee_ids: assigneeIds, label_ids: labelIds },
    });
  }
  parseNLP(text) {
    return this._fetch(`/tasks/nlp/parse?text=${encodeURIComponent(text)}`, { method: 'POST' });
  }
  updateTask(id, data) {
    return this._fetch(`/tasks/${id}`, { method: 'PUT', body: data });
  }
  deleteTask(id) {
    return this._fetch(`/tasks/${id}`, { method: 'DELETE' });
  }
  completeTask(taskId, userId, notes = null) {
    return this._fetch(`/tasks/${taskId}/complete`, {
      method: 'POST',
      body: { user_id: userId, notes },
    });
  }

  // ── Time Tracking ──
  startTimeSession(taskId, userId) {
    return this._fetch('/tasks/time/start', { method: 'POST', body: { task_id: taskId, user_id: userId } });
  }
  stopTimeSession(sessionId) {
    return this._fetch('/tasks/time/stop', { method: 'POST', body: { session_id: sessionId } });
  }
  getTaskTimeSessions(taskId) {
    return this._fetch(`/tasks/${taskId}/time`);
  }

  // ── Labels ──
  getLabels() {
    return this._fetch('/labels/');
  }
  createLabel(data) {
    return this._fetch('/labels/', { method: 'POST', body: data });
  }
  updateLabel(id, data) {
    return this._fetch(`/labels/${id}`, { method: 'PUT', body: data });
  }
  deleteLabel(id) {
    return this._fetch(`/labels/${id}`, { method: 'DELETE' });
  }

  // ── Photos ──
  uploadPhoto(taskId, file) {
    const formData = new FormData();
    formData.append('file', file);
    return this._fetch(`/photos/upload/${taskId}`, { method: 'POST', body: formData });
  }
  getPhotoUrl(photoId) {
    return `${this.baseUrl}/api/photos/${photoId}`;
  }
  getThumbnailUrl(photoId) {
    return `${this.baseUrl}/api/photos/${photoId}/thumbnail`;
  }

  getBaseUrl() {
    return this.baseUrl;
  }
  deletePhoto(photoId) {
    return this._fetch(`/photos/${photoId}`, { method: 'DELETE' });
  }

  // ── Analytics ──
  getOverview() {
    return this._fetch('/analytics/overview');
  }
  getUserStats(userId) {
    return this._fetch(`/analytics/users/${userId}`);
  }
  getLeaderboard(limit = 10) {
    return this._fetch(`/analytics/leaderboard?limit=${limit}`);
  }
  getCompletionHistory(days = 30, userId = null) {
    const params = new URLSearchParams({ days });
    if (userId) params.set('user_id', userId);
    return this._fetch(`/analytics/completions?${params}`);
  }
}

// Singleton
export const api = new HacpmApi();
