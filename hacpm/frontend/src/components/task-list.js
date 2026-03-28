/**
 * Task List Component
 * Shows filterable, sortable list of tasks with quick-complete actions.
 */

import { LitElement, html, css } from 'lit';
import { api } from '../services/api.js';

class TaskList extends LitElement {
  static properties = {
    tasks: { type: Array },
    labels: { type: Array },
    currentUser: { type: Object },
    users: { type: Array },
    filterStatus: { type: String },
    filterLabel: { type: String },
    filterAssignee: { type: String },
    searchQuery: { type: String },
    _loading: { type: Boolean, state: true },
  };

  static styles = css`
    :host { display: block; }

    .filters {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-bottom: 16px;
      align-items: center;
    }
    .search-input {
      flex: 1;
      min-width: 200px;
      padding: 8px 12px;
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 8px;
      font-size: 14px;
      outline: none;
      background: var(--bg-card, #fff);
      color: var(--text-primary, #212121);
      font-family: inherit;
    }
    .search-input:focus { border-color: var(--primary-color, #03a9f4); }

    select {
      padding: 8px 12px;
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 8px;
      font-size: 13px;
      background: var(--bg-card, #fff);
      color: var(--text-primary, #212121);
      font-family: inherit;
      cursor: pointer;
    }

    .task-card {
      background: var(--bg-card, #fff);
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 10px;
      padding: 14px 16px;
      margin-bottom: 8px;
      display: flex;
      align-items: center;
      gap: 12px;
      cursor: pointer;
      transition: all 0.15s;
    }
    .task-card:hover {
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      border-color: var(--primary-color, #03a9f4);
    }
    .task-card.overdue { border-left: 3px solid var(--error-color, #f44336); }
    .task-card.completed { opacity: 0.6; }

    .check-btn {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      border: 2px solid #bdbdbd;
      background: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
      transition: all 0.2s;
      font-size: 14px;
      color: transparent;
    }
    .check-btn:hover {
      border-color: var(--success-color, #4caf50);
      background: rgba(76,175,80,0.1);
      color: var(--success-color, #4caf50);
    }
    .check-btn.completed {
      border-color: var(--success-color, #4caf50);
      background: var(--success-color, #4caf50);
      color: white;
    }
    .check-btn.restricted {
      border-color: #e0e0e0;
      cursor: not-allowed;
      opacity: 0.4;
    }

    .task-info { flex: 1; min-width: 0; }
    .task-title {
      font-size: 15px;
      font-weight: 500;
      margin-bottom: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .task-meta {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      align-items: center;
      font-size: 12px;
      color: var(--text-secondary, #757575);
    }

    .priority-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .priority-low { background: #4caf50; }
    .priority-medium { background: #ff9800; }
    .priority-high { background: #f44336; }
    .priority-critical { background: #9c27b0; }

    .label-chip {
      padding: 1px 8px;
      border-radius: 10px;
      font-size: 11px;
      font-weight: 500;
      color: white;
    }

    .assignee-chip {
      padding: 1px 6px;
      border-radius: 10px;
      background: #e3f2fd;
      color: #1976d2;
      font-size: 11px;
    }

    .due-date { font-size: 12px; }
    .due-date.overdue { color: var(--error-color, #f44336); font-weight: 600; }
    .due-date.today { color: var(--warning-color, #ff9800); font-weight: 600; }

    .points {
      background: var(--accent-color, #ff9800);
      color: white;
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 11px;
      font-weight: 600;
      flex-shrink: 0;
    }

    .empty-state {
      text-align: center;
      padding: 60px 20px;
      color: var(--text-secondary, #757575);
    }
    .empty-state .icon { font-size: 48px; margin-bottom: 16px; }

    .subtask-count {
      font-size: 11px;
      color: var(--text-secondary, #757575);
    }

    .recurrence-badge {
      font-size: 11px;
      color: #7c4dff;
    }
  `;

  constructor() {
    super();
    this.tasks = [];
    this.labels = [];
    this.currentUser = null;
    this.users = [];
    this.filterStatus = '';
    this.filterLabel = '';
    this.filterAssignee = '';
    this.searchQuery = '';
    this._loading = false;
  }

  async connectedCallback() {
    super.connectedCallback();
    if (this.tasks.length === 0) {
      this._loading = true;
      try {
        this.tasks = await api.getTasks();
      } catch { /* parent handles */ }
      this._loading = false;
    }
  }

  get filteredTasks() {
    let list = [...this.tasks];

    if (this.searchQuery) {
      const q = this.searchQuery.toLowerCase();
      list = list.filter(t => t.title.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q));
    }
    if (this.filterStatus) {
      list = list.filter(t => t.status === this.filterStatus);
    }
    if (this.filterLabel) {
      const lid = parseInt(this.filterLabel);
      list = list.filter(t => t.labels.some(l => l.id === lid));
    }
    if (this.filterAssignee) {
      const uid = parseInt(this.filterAssignee);
      list = list.filter(t => t.assignees.some(u => u.id === uid));
    }

    return list;
  }

  render() {
    if (this._loading) {
      return html`<div class="empty-state">Loading tasks...</div>`;
    }

    return html`
      <!-- Filters -->
      <div class="filters">
        <input
          class="search-input"
          type="text"
          placeholder="Search tasks..."
          .value=${this.searchQuery}
          @input=${(e) => { this.searchQuery = e.target.value; }}
        >
        <select @change=${(e) => { this.filterStatus = e.target.value; }}>
          <option value="">All Status</option>
          <option value="pending">Pending</option>
          <option value="in_progress">In Progress</option>
          <option value="completed">Completed</option>
          <option value="overdue">Overdue</option>
        </select>
        <select @change=${(e) => { this.filterLabel = e.target.value; }}>
          <option value="">All Labels</option>
          ${this.labels.map(l => html`<option value=${l.id}>${l.name}</option>`)}
        </select>
        <select @change=${(e) => { this.filterAssignee = e.target.value; }}>
          <option value="">All Assignees</option>
          ${this.users.map(u => html`<option value=${u.id}>${u.display_name || u.name}</option>`)}
        </select>
      </div>

      <!-- Task List -->
      ${this.filteredTasks.length === 0 ? html`
        <div class="empty-state">
          <div class="icon">&#x2611;</div>
          <p>No tasks found. Create one with the + button!</p>
        </div>
      ` : this.filteredTasks.map(task => this._renderTask(task))}
    `;
  }

  _renderTask(task) {
    const isCompleted = task.status === 'completed';
    const isOverdue = task.status === 'overdue';
    const dueStr = this._formatDueDate(task.due_date);

    return html`
      <div
        class="task-card ${isOverdue ? 'overdue' : ''} ${isCompleted ? 'completed' : ''}"
        @click=${() => this.dispatchEvent(new CustomEvent('task-selected', { detail: { task } }))}
      >
        <button
          class="check-btn ${isCompleted ? 'completed' : ''} ${!task.can_complete ? 'restricted' : ''}"
          @click=${(e) => { e.stopPropagation(); this._completeTask(task); }}
          ?disabled=${isCompleted || !task.can_complete}
          title=${!task.can_complete ? 'Cannot complete yet' : 'Mark complete'}
        >
          ${isCompleted ? '&#x2713;' : ''}
        </button>

        <span class="priority-dot priority-${task.priority}"></span>

        <div class="task-info">
          <div class="task-title">${task.title}</div>
          <div class="task-meta">
            ${dueStr ? html`<span class="due-date ${isOverdue ? 'overdue' : ''} ${this._isToday(task.due_date) ? 'today' : ''}">${dueStr}</span>` : ''}
            ${task.recurrence_rule ? html`<span class="recurrence-badge">&#x1f504; Recurring</span>` : ''}
            ${task.labels.map(l => html`<span class="label-chip" style="background:${l.color}">${l.name}</span>`)}
            ${task.assignees.map(u => html`<span class="assignee-chip">${u.display_name || u.name}</span>`)}
            ${task.subtasks.length > 0 ? html`
              <span class="subtask-count">
                ${task.subtasks.filter(s => s.status === 'completed').length}/${task.subtasks.length} subtasks
              </span>
            ` : ''}
          </div>
        </div>

        <span class="points">${task.effective_points} pts</span>
      </div>
    `;
  }

  _completeTask(task) {
    if (task.status === 'completed' || !task.can_complete) return;
    this.dispatchEvent(new CustomEvent('task-completed', { detail: { taskId: task.id } }));
  }

  _formatDueDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diff = Math.floor((date - now) / (1000 * 60 * 60 * 24));

    if (diff < 0) return `${Math.abs(diff)}d overdue`;
    if (diff === 0) return 'Today';
    if (diff === 1) return 'Tomorrow';
    if (diff < 7) return date.toLocaleDateString('en-US', { weekday: 'short' });
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  _isToday(dateStr) {
    if (!dateStr) return false;
    const date = new Date(dateStr);
    const today = new Date();
    return date.toDateString() === today.toDateString();
  }
}

customElements.define('task-list', TaskList);
