/**
 * Task Detail Component
 * Shows full task details, subtasks, photos, time tracking, and history.
 */

import { LitElement, html, css } from 'lit';
import { api } from '../services/api.js';

class TaskDetail extends LitElement {
  static properties = {
    task: { type: Object },
    users: { type: Array },
    labels: { type: Array },
    currentUser: { type: Object },
    _editing: { type: Boolean, state: true },
    _activeSession: { type: Object, state: true },
    _history: { type: Array, state: true },
    _showSubtaskForm: { type: Boolean, state: true },
    _subtaskTitle: { type: String, state: true },
    _error: { type: String, state: true },
  };

  static styles = css`
    :host { display: block; }

    .back-btn {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      background: none;
      border: none;
      color: var(--primary-color, #03a9f4);
      cursor: pointer;
      font-size: 14px;
      padding: 4px 0;
      margin-bottom: 12px;
      font-family: inherit;
    }

    .detail-card {
      background: var(--bg-card, #fff);
      border-radius: 12px;
      border: 1px solid var(--border-color, #e0e0e0);
      padding: 24px;
    }

    .task-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 16px;
    }
    .task-title { font-size: 22px; font-weight: 600; flex: 1; }
    .status-badge {
      padding: 4px 12px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
      text-transform: uppercase;
    }
    .status-pending { background: #fff3e0; color: #e65100; }
    .status-in_progress { background: #e3f2fd; color: #1565c0; }
    .status-completed { background: #e8f5e9; color: #2e7d32; }
    .status-overdue { background: #fce4ec; color: #c62828; }

    .meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 20px;
    }
    .meta-item {
      font-size: 13px;
    }
    .meta-label {
      color: var(--text-secondary, #757575);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    .meta-value { font-weight: 500; }

    .description {
      background: var(--bg-primary, #fafafa);
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 20px;
      font-size: 14px;
      white-space: pre-wrap;
    }

    .section {
      margin-top: 24px;
    }
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }
    .section h3 {
      font-size: 16px;
      font-weight: 600;
    }

    /* Subtasks */
    .subtask-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 0;
      border-bottom: 1px solid var(--border-color, #e0e0e0);
    }
    .subtask-check {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      border: 2px solid #bdbdbd;
      background: none;
      cursor: pointer;
      font-size: 10px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: transparent;
      flex-shrink: 0;
    }
    .subtask-check.done {
      border-color: var(--success-color, #4caf50);
      background: var(--success-color, #4caf50);
      color: white;
    }
    .subtask-title { font-size: 14px; flex: 1; }
    .subtask-title.done { text-decoration: line-through; color: var(--text-secondary); }

    .subtask-form {
      display: flex;
      gap: 8px;
      margin-top: 8px;
    }
    .subtask-form input {
      flex: 1;
      padding: 8px;
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 6px;
      font-size: 13px;
      font-family: inherit;
      outline: none;
    }

    /* Photos */
    .photo-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 8px;
    }
    .photo-thumb {
      width: 100%;
      aspect-ratio: 1;
      object-fit: cover;
      border-radius: 8px;
      cursor: pointer;
    }
    .photo-upload {
      width: 100%;
      aspect-ratio: 1;
      border: 2px dashed var(--border-color, #e0e0e0);
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 24px;
      color: var(--text-secondary, #757575);
    }

    /* Time tracking */
    .timer {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .timer-btn {
      padding: 8px 20px;
      border-radius: 8px;
      border: none;
      cursor: pointer;
      font-size: 14px;
      font-family: inherit;
      font-weight: 500;
    }
    .timer-start { background: var(--success-color, #4caf50); color: white; }
    .timer-stop { background: var(--error-color, #f44336); color: white; }
    .timer-display {
      font-size: 20px;
      font-weight: 600;
      font-variant-numeric: tabular-nums;
    }

    /* Actions */
    .action-bar {
      display: flex;
      gap: 8px;
      margin-top: 24px;
      flex-wrap: wrap;
    }
    .btn {
      padding: 10px 20px;
      border-radius: 8px;
      font-size: 14px;
      cursor: pointer;
      border: none;
      font-family: inherit;
      font-weight: 500;
    }
    .btn-complete { background: var(--success-color, #4caf50); color: white; }
    .btn-complete:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-delete { background: var(--error-color, #f44336); color: white; }
    .btn-secondary {
      background: var(--bg-primary, #fafafa);
      color: var(--text-primary);
      border: 1px solid var(--border-color, #e0e0e0);
    }

    .error { color: var(--error-color, #f44336); font-size: 13px; margin-top: 8px; }

    .label-chip {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 10px;
      font-size: 12px;
      color: white;
      margin-right: 4px;
    }
    .assignee-chip {
      display: inline-block;
      padding: 2px 10px;
      border-radius: 10px;
      background: #e3f2fd;
      color: #1976d2;
      font-size: 12px;
      margin-right: 4px;
    }

    .history-item {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px solid var(--border-color, #e0e0e0);
      font-size: 13px;
    }

    /* Nested subtasks */
    .nested { margin-left: 24px; }
  `;

  constructor() {
    super();
    this.task = null;
    this.users = [];
    this.labels = [];
    this.currentUser = null;
    this._editing = false;
    this._activeSession = null;
    this._history = [];
    this._showSubtaskForm = false;
    this._subtaskTitle = '';
    this._error = '';
  }

  async connectedCallback() {
    super.connectedCallback();
    if (this.task) {
      await this._loadHistory();
    }
  }

  async _loadHistory() {
    try {
      this._history = await api.getTaskTimeSessions(this.task.id);
    } catch { /* ignore */ }
  }

  render() {
    if (!this.task) return html`<div>No task selected</div>`;

    const t = this.task;

    return html`
      <button class="back-btn" @click=${() => this.dispatchEvent(new CustomEvent('back'))}>
        &#8592; Back to tasks
      </button>

      <div class="detail-card">
        <div class="task-header">
          <div class="task-title">${t.title}</div>
          <span class="status-badge status-${t.status}">${t.status.replace('_', ' ')}</span>
        </div>

        ${t.description ? html`<div class="description">${t.description}</div>` : ''}

        <div class="meta-grid">
          <div class="meta-item">
            <div class="meta-label">Priority</div>
            <div class="meta-value" style="text-transform:capitalize">${t.priority}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Points</div>
            <div class="meta-value">${t.effective_points} pts</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Due Date</div>
            <div class="meta-value">${t.due_date ? new Date(t.due_date).toLocaleString() : 'None'}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Recurrence</div>
            <div class="meta-value">${t.recurrence_rule || 'One-time'}</div>
          </div>
          <div class="meta-item">
            <div class="meta-label">Time Tracked</div>
            <div class="meta-value">${this._formatDuration(t.total_time_seconds)}</div>
          </div>
          ${t.completion_restriction_hours ? html`
            <div class="meta-item">
              <div class="meta-label">Completion Window</div>
              <div class="meta-value">Last ${t.completion_restriction_hours} hours before due</div>
            </div>
          ` : ''}
        </div>

        <!-- Assignees -->
        <div class="meta-item" style="margin-bottom: 12px;">
          <div class="meta-label">Assigned To</div>
          <div>${t.assignees.length > 0
            ? t.assignees.map(u => html`<span class="assignee-chip">${u.name}</span>`)
            : 'Unassigned'
          }</div>
        </div>

        <!-- Labels -->
        <div class="meta-item">
          <div class="meta-label">Labels</div>
          <div>${t.labels.length > 0
            ? t.labels.map(l => html`<span class="label-chip" style="background:${l.color}">${l.name}</span>`)
            : 'None'
          }</div>
        </div>

        <!-- Subtasks -->
        <div class="section">
          <div class="section-header">
            <h3>Subtasks (${t.subtasks.filter(s => s.status === 'completed').length}/${t.subtasks.length})</h3>
            <button class="btn btn-secondary" @click=${() => { this._showSubtaskForm = !this._showSubtaskForm; }}>
              + Add Subtask
            </button>
          </div>
          ${this._renderSubtasks(t.subtasks, 0)}
          ${this._showSubtaskForm ? html`
            <div class="subtask-form">
              <input type="text" placeholder="Subtask title..."
                .value=${this._subtaskTitle}
                @input=${(e) => { this._subtaskTitle = e.target.value; }}
                @keyup=${(e) => { if (e.key === 'Enter') this._addSubtask(); }}>
              <button class="btn btn-secondary" @click=${this._addSubtask}>Add</button>
            </div>
          ` : ''}
        </div>

        <!-- Photos -->
        <div class="section">
          <h3>Photos</h3>
          <div class="photo-grid">
            ${(t.photos || []).map(p => html`
              <img class="photo-thumb" src="${api.getPhotoUrl(p.id)}" alt="${p.filename}">
            `)}
            <label class="photo-upload">
              +
              <input type="file" accept="image/*" hidden @change=${this._uploadPhoto}>
            </label>
          </div>
        </div>

        <!-- Time Tracking -->
        <div class="section">
          <h3>Time Tracking</h3>
          <div class="timer">
            ${this._activeSession ? html`
              <button class="timer-btn timer-stop" @click=${this._stopTimer}>Stop Timer</button>
              <span class="timer-display">Tracking...</span>
            ` : html`
              <button class="timer-btn timer-start" @click=${this._startTimer}>Start Timer</button>
            `}
          </div>
        </div>

        ${this._error ? html`<div class="error">${this._error}</div>` : ''}

        <!-- Actions -->
        <div class="action-bar">
          <button class="btn btn-complete"
            ?disabled=${t.status === 'completed' || !t.can_complete}
            @click=${() => this.dispatchEvent(new CustomEvent('task-completed', { detail: { taskId: t.id } }))}>
            ${t.status === 'completed' ? 'Completed' : 'Mark Complete'}
          </button>
          <button class="btn btn-delete" @click=${this._deleteTask}>Delete</button>
        </div>
      </div>
    `;
  }

  _renderSubtasks(subtasks, depth) {
    if (!subtasks || subtasks.length === 0) return '';
    return html`
      <div class="${depth > 0 ? 'nested' : ''}">
        ${subtasks.map(st => html`
          <div class="subtask-item">
            <button
              class="subtask-check ${st.status === 'completed' ? 'done' : ''}"
              @click=${() => this._toggleSubtask(st)}
            >
              ${st.status === 'completed' ? '&#x2713;' : ''}
            </button>
            <span class="subtask-title ${st.status === 'completed' ? 'done' : ''}">${st.title}</span>
          </div>
          ${st.subtasks ? this._renderSubtasks(st.subtasks, depth + 1) : ''}
        `)}
      </div>
    `;
  }

  async _toggleSubtask(subtask) {
    try {
      const newStatus = subtask.status === 'completed' ? 'pending' : 'completed';
      await api.updateTask(subtask.id, { status: newStatus });
      // Refresh parent task
      this.task = await api.getTask(this.task.id);
      this.dispatchEvent(new CustomEvent('task-updated'));
    } catch (e) {
      this._error = e.message;
    }
  }

  async _addSubtask() {
    if (!this._subtaskTitle.trim()) return;
    try {
      await api.createTask({
        title: this._subtaskTitle,
        parent_task_id: this.task.id,
        created_by: this.currentUser?.id,
        assignee_ids: [],
        label_ids: [],
      });
      this._subtaskTitle = '';
      this._showSubtaskForm = false;
      this.task = await api.getTask(this.task.id);
      this.dispatchEvent(new CustomEvent('task-updated'));
    } catch (e) {
      this._error = e.message;
    }
  }

  async _uploadPhoto(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await api.uploadPhoto(this.task.id, file);
      this.task = await api.getTask(this.task.id);
    } catch (err) {
      this._error = err.message;
    }
  }

  async _startTimer() {
    try {
      this._activeSession = await api.startTimeSession(this.task.id, this.currentUser?.id);
    } catch (e) {
      this._error = e.message;
    }
  }

  async _stopTimer() {
    if (!this._activeSession) return;
    try {
      await api.stopTimeSession(this._activeSession.id);
      this._activeSession = null;
      this.task = await api.getTask(this.task.id);
    } catch (e) {
      this._error = e.message;
    }
  }

  async _deleteTask() {
    if (!confirm('Delete this task and all subtasks?')) return;
    try {
      await api.deleteTask(this.task.id);
      this.dispatchEvent(new CustomEvent('back'));
    } catch (e) {
      this._error = e.message;
    }
  }

  _formatDuration(seconds) {
    if (!seconds) return '0m';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }
}

customElements.define('task-detail', TaskDetail);
