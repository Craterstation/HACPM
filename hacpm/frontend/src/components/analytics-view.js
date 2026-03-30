/**
 * Analytics View Component
 * Shows task completion stats, charts, and per-user breakdowns.
 */

import { LitElement, html, css } from 'lit';
import { api } from '../services/api.js';

class AnalyticsView extends LitElement {
  static properties = {
    currentUser: { type: Object },
    users: { type: Array },
    _overview: { type: Object, state: true },
    _userStats: { type: Object, state: true },
    _completionHistory: { type: Array, state: true },
    _selectedUserId: { type: Number, state: true },
    _loading: { type: Boolean, state: true },
  };

  static styles = css`
    :host { display: block; }

    h2 { font-size: 20px; font-weight: 600; margin-bottom: 20px; }

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      margin-bottom: 24px;
    }
    .stat-card {
      background: var(--bg-card, #fff);
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 10px;
      padding: 16px;
      text-align: center;
    }
    .stat-value {
      font-size: 28px;
      font-weight: 700;
      color: var(--primary-color, #03a9f4);
    }
    .stat-label {
      font-size: 12px;
      color: var(--text-secondary, #757575);
      margin-top: 4px;
    }

    .section {
      background: var(--bg-card, #fff);
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 10px;
      padding: 20px;
      margin-bottom: 20px;
    }
    .section h3 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
    }

    /* Simple bar chart */
    .bar-chart {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .bar-row {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .bar-label {
      width: 100px;
      font-size: 13px;
      text-align: right;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .bar-track {
      flex: 1;
      height: 24px;
      background: var(--bg-primary, #fafafa);
      border-radius: 12px;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%;
      border-radius: 12px;
      display: flex;
      align-items: center;
      padding-left: 8px;
      font-size: 12px;
      color: white;
      font-weight: 600;
      min-width: 30px;
      transition: width 0.5s ease;
    }

    .user-select {
      padding: 8px 12px;
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 8px;
      font-size: 13px;
      margin-bottom: 16px;
      font-family: inherit;
    }

    /* Completion trend */
    .trend-row {
      display: flex;
      align-items: flex-end;
      gap: 2px;
      height: 100px;
      padding: 8px 0;
    }
    .trend-bar {
      flex: 1;
      background: var(--primary-color, #03a9f4);
      border-radius: 3px 3px 0 0;
      min-width: 6px;
      transition: height 0.3s ease;
    }
    .trend-labels {
      display: flex;
      justify-content: space-between;
      font-size: 10px;
      color: var(--text-secondary, #757575);
    }

    .loading { text-align: center; padding: 40px; color: var(--text-secondary); }

    .completion-rate {
      font-size: 36px;
      font-weight: 700;
      color: var(--success-color, #4caf50);
    }
  `;

  constructor() {
    super();
    this.currentUser = null;
    this.users = [];
    this._overview = null;
    this._userStats = null;
    this._completionHistory = [];
    this._selectedUserId = null;
    this._loading = true;
  }

  async connectedCallback() {
    super.connectedCallback();
    await this._loadData();
  }

  async _loadData() {
    this._loading = true;
    try {
      const [overview, history] = await Promise.all([
        api.getOverview(),
        api.getCompletionHistory(30),
      ]);
      this._overview = overview;
      this._completionHistory = history;

      if (this.currentUser) {
        this._selectedUserId = this.currentUser.id;
        this._userStats = await api.getUserStats(this.currentUser.id);
      }
    } catch { /* ignore */ }
    this._loading = false;
  }

  async _onUserChange(e) {
    this._selectedUserId = parseInt(e.target.value);
    if (this._selectedUserId) {
      this._userStats = await api.getUserStats(this._selectedUserId);
    }
  }

  render() {
    if (this._loading) return html`<div class="loading">Loading analytics...</div>`;

    const o = this._overview;
    if (!o) return html`<div>No data available</div>`;

    return html`
      <h2>Analytics</h2>

      <!-- Overview Stats -->
      <div class="stat-grid">
        <div class="stat-card">
          <div class="stat-value">${o.total_tasks}</div>
          <div class="stat-label">Total Tasks</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${o.completed_tasks}</div>
          <div class="stat-label">Completed</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${o.pending_tasks}</div>
          <div class="stat-label">Pending</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${o.overdue_tasks}</div>
          <div class="stat-label">Overdue</div>
        </div>
        <div class="stat-card">
          <div class="completion-rate">${o.completion_rate}%</div>
          <div class="stat-label">Completion Rate</div>
        </div>
      </div>

      <!-- Completion Trend -->
      ${this._completionHistory.length > 0 ? html`
        <div class="section">
          <h3>Completion Trend (Last 30 Days)</h3>
          ${this._renderTrend()}
        </div>
      ` : ''}

      <!-- Tasks by Priority -->
      ${Object.keys(o.tasks_by_priority).length > 0 ? html`
        <div class="section">
          <h3>Tasks by Priority</h3>
          ${this._renderBarChart(o.tasks_by_priority, {
            low: '#4caf50', medium: '#ff9800', high: '#f44336', critical: '#9c27b0'
          })}
        </div>
      ` : ''}

      <!-- Tasks by Label -->
      ${Object.keys(o.tasks_by_label).length > 0 ? html`
        <div class="section">
          <h3>Tasks by Label</h3>
          ${this._renderBarChart(o.tasks_by_label)}
        </div>
      ` : ''}

      <!-- Per-User Stats -->
      <div class="section">
        <h3>User Stats</h3>
        <select class="user-select" @change=${this._onUserChange}>
          <option value="">Select a user</option>
          ${this.users.map(u => html`
            <option value=${u.id} ?selected=${u.id === this._selectedUserId}>
              ${u.name}
            </option>
          `)}
        </select>

        ${this._userStats ? html`
          <div class="stat-grid">
            <div class="stat-card">
              <div class="stat-value">${this._userStats.total_points}</div>
              <div class="stat-label">Total Points</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">${this._userStats.tasks_completed}</div>
              <div class="stat-label">Completed</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">${this._userStats.tasks_pending}</div>
              <div class="stat-label">Pending</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">${this._formatDuration(this._userStats.total_time_seconds)}</div>
              <div class="stat-label">Time Tracked</div>
            </div>
          </div>

          ${Object.keys(this._userStats.completions_by_label).length > 0 ? html`
            <h3 style="margin-top:16px">Completions by Label</h3>
            ${this._renderBarChart(this._userStats.completions_by_label)}
          ` : ''}
        ` : ''}
      </div>
    `;
  }

  _renderBarChart(data, colorMap = {}) {
    const max = Math.max(...Object.values(data), 1);
    const defaultColors = ['#03a9f4', '#4caf50', '#ff9800', '#9c27b0', '#f44336', '#607d8b'];

    return html`
      <div class="bar-chart">
        ${Object.entries(data).map(([key, value], i) => {
          const pct = (value / max) * 100;
          const color = colorMap[key] || defaultColors[i % defaultColors.length];
          return html`
            <div class="bar-row">
              <span class="bar-label">${key}</span>
              <div class="bar-track">
                <div class="bar-fill" style="width:${pct}%;background:${color}">${value}</div>
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }

  _renderTrend() {
    const data = this._completionHistory;
    const max = Math.max(...data.map(d => d.count), 1);

    return html`
      <div class="trend-row">
        ${data.map(d => html`
          <div class="trend-bar" style="height:${(d.count / max) * 100}%"
            title="${d.date}: ${d.count} completed, ${d.points} pts"></div>
        `)}
      </div>
      <div class="trend-labels">
        <span>${data[0]?.date || ''}</span>
        <span>${data[data.length - 1]?.date || ''}</span>
      </div>
    `;
  }

  _formatDuration(seconds) {
    if (!seconds) return '0m';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }
}

customElements.define('analytics-view', AnalyticsView);
