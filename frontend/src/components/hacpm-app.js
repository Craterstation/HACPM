/**
 * HACPM Main Application Shell
 *
 * Provides navigation, user selection, and renders the appropriate view.
 * Adapts layout for tablet/desktop (sidebar) vs mobile (bottom nav).
 */

import { LitElement, html, css } from 'lit';
import { api } from '../services/api.js';
import { ws } from '../services/websocket.js';
import './user-picker.js';
import './task-list.js';
import './task-form.js';
import './task-detail.js';
import './analytics-view.js';
import './admin-panel.js';
import './leaderboard-view.js';

class HacpmApp extends LitElement {
  static properties = {
    currentView: { type: String },
    currentUser: { type: Object },
    users: { type: Array },
    tasks: { type: Array },
    labels: { type: Array },
    selectedTask: { type: Object },
    showUserPicker: { type: Boolean },
    loading: { type: Boolean },
    error: { type: String },
  };

  static styles = css`
    :host {
      display: block;
      min-height: 100vh;
      background: var(--bg-primary, #fafafa);
      color: var(--text-primary, #212121);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    .app-container {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }

    /* Header */
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 20px;
      background: var(--primary-color, #03a9f4);
      color: white;
      box-shadow: 0 2px 4px rgba(0,0,0,0.2);
      z-index: 10;
    }
    .header h1 {
      font-size: 18px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .header-actions {
      display: flex;
      gap: 8px;
      align-items: center;
    }
    .user-badge {
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(255,255,255,0.2);
      padding: 4px 12px;
      border-radius: 20px;
      cursor: pointer;
      font-size: 14px;
      border: none;
      color: white;
    }
    .user-badge:hover { background: rgba(255,255,255,0.3); }
    .avatar {
      width: 28px;
      height: 28px;
      border-radius: 50%;
      background: rgba(255,255,255,0.3);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
    }
    .points-badge {
      background: var(--accent-color, #ff9800);
      color: white;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 600;
    }

    /* Main content */
    .main {
      flex: 1;
      padding: 16px;
      max-width: 1200px;
      margin: 0 auto;
      width: 100%;
    }

    /* Desktop layout with sidebar */
    @media (min-width: 768px) {
      .app-container { flex-direction: column; }
      .content-area {
        display: flex;
        flex: 1;
      }
      .sidebar {
        width: 220px;
        background: var(--bg-card, #fff);
        border-right: 1px solid var(--border-color, #e0e0e0);
        padding: 16px 0;
        display: flex;
        flex-direction: column;
      }
      .main { flex: 1; }
    }
    @media (max-width: 767px) {
      .sidebar { display: none; }
    }

    /* Navigation */
    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 20px;
      cursor: pointer;
      color: var(--text-secondary, #757575);
      transition: all 0.15s;
      border: none;
      background: none;
      width: 100%;
      text-align: left;
      font-size: 14px;
      font-family: inherit;
    }
    .nav-item:hover {
      background: var(--bg-primary, #fafafa);
      color: var(--text-primary);
    }
    .nav-item.active {
      color: var(--primary-color, #03a9f4);
      background: rgba(3, 169, 244, 0.08);
      border-left: 3px solid var(--primary-color, #03a9f4);
    }
    .nav-icon { font-size: 18px; width: 24px; text-align: center; }

    /* Bottom nav for mobile */
    .bottom-nav {
      display: none;
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      background: var(--bg-card, #fff);
      border-top: 1px solid var(--border-color, #e0e0e0);
      z-index: 10;
      padding: 4px 0;
    }
    @media (max-width: 767px) {
      .bottom-nav {
        display: flex;
        justify-content: space-around;
      }
      .main { padding-bottom: 70px; }
    }
    .bottom-nav-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      padding: 6px 12px;
      cursor: pointer;
      color: var(--text-secondary, #757575);
      font-size: 10px;
      border: none;
      background: none;
      font-family: inherit;
    }
    .bottom-nav-item.active {
      color: var(--primary-color, #03a9f4);
    }
    .bottom-nav-item .nav-icon { font-size: 22px; }

    /* FAB */
    .fab {
      position: fixed;
      bottom: 80px;
      right: 20px;
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: var(--primary-color, #03a9f4);
      color: white;
      border: none;
      font-size: 28px;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(3,169,244,0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 5;
      transition: transform 0.2s;
    }
    .fab:hover { transform: scale(1.1); }
    @media (min-width: 768px) {
      .fab { bottom: 24px; right: 24px; }
    }

    /* Loading / Error */
    .loading {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 60px;
      color: var(--text-secondary);
    }
    .error-banner {
      background: var(--error-color, #f44336);
      color: white;
      padding: 8px 16px;
      text-align: center;
      font-size: 14px;
    }
  `;

  constructor() {
    super();
    this.currentView = 'tasks';
    this.currentUser = null;
    this.users = [];
    this.tasks = [];
    this.labels = [];
    this.selectedTask = null;
    this.showUserPicker = true;
    this.loading = true;
    this.error = '';
  }

  async connectedCallback() {
    super.connectedCallback();
    await this._loadInitialData();
    this._setupWebSocket();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    ws.disconnect();
  }

  async _loadInitialData() {
    try {
      this.loading = true;
      const [users, labels] = await Promise.all([
        api.getUsers(),
        api.getLabels(),
      ]);
      this.users = users;
      this.labels = labels;

      // If only one user or user previously selected, auto-login
      const savedUserId = localStorage.getItem('hacpm_user_id');
      if (savedUserId) {
        const user = users.find(u => u.id === parseInt(savedUserId));
        if (user) {
          this.currentUser = user;
          this.showUserPicker = false;
        }
      }
      if (users.length === 0) {
        // First run — go to admin to create users
        this.showUserPicker = false;
        this.currentView = 'admin';
      }
    } catch (e) {
      this.error = `Failed to load data: ${e.message}`;
    } finally {
      this.loading = false;
    }
  }

  async _loadTasks() {
    try {
      this.tasks = await api.getTasks();
    } catch (e) {
      this.error = `Failed to load tasks: ${e.message}`;
    }
  }

  _setupWebSocket() {
    ws.connect(this.currentUser?.id);

    ws.on('task_created', () => this._loadTasks());
    ws.on('task_updated', () => this._loadTasks());
    ws.on('task_deleted', () => this._loadTasks());
    ws.on('task_completed', () => {
      this._loadTasks();
      this._refreshUser();
    });
    ws.on('user_updated', () => this._loadInitialData());
  }

  async _refreshUser() {
    if (!this.currentUser) return;
    try {
      this.currentUser = await api.getUser(this.currentUser.id);
    } catch { /* ignore */ }
  }

  _selectUser(e) {
    this.currentUser = e.detail.user;
    localStorage.setItem('hacpm_user_id', this.currentUser.id);
    this.showUserPicker = false;
    this._loadTasks();
    ws.disconnect();
    ws.connect(this.currentUser.id);
  }

  _switchUser() {
    this.showUserPicker = true;
  }

  _navigate(view) {
    this.currentView = view;
    this.selectedTask = null;
  }

  _openTaskDetail(e) {
    this.selectedTask = e.detail.task;
    this.currentView = 'detail';
  }

  _openNewTask() {
    this.currentView = 'new-task';
  }

  _backToList() {
    this.currentView = 'tasks';
    this.selectedTask = null;
    this._loadTasks();
  }

  get isAdmin() {
    return this.currentUser?.role === 'parent';
  }

  render() {
    if (this.showUserPicker) {
      return html`
        <user-picker
          .users=${this.users}
          @user-selected=${this._selectUser}
          @manage-users=${() => { this.showUserPicker = false; this.currentView = 'admin'; }}
        ></user-picker>
      `;
    }

    return html`
      <div class="app-container">
        ${this.error ? html`<div class="error-banner">${this.error}</div>` : ''}

        <!-- Header -->
        <div class="header">
          <h1>
            <span>&#x1f3e0;</span> HACPM
          </h1>
          <div class="header-actions">
            ${this.currentUser ? html`
              <span class="points-badge">${this.currentUser.total_points || 0} pts</span>
              <button class="user-badge" @click=${this._switchUser}>
                <span class="avatar">${this.currentUser.name?.[0] || '?'}</span>
                ${this.currentUser.display_name || this.currentUser.name}
              </button>
            ` : ''}
          </div>
        </div>

        <div class="content-area">
          <!-- Sidebar (desktop) -->
          <nav class="sidebar">
            <button class="nav-item ${this.currentView === 'tasks' ? 'active' : ''}"
              @click=${() => this._navigate('tasks')}>
              <span class="nav-icon">&#x2611;</span> Tasks
            </button>
            <button class="nav-item ${this.currentView === 'analytics' ? 'active' : ''}"
              @click=${() => this._navigate('analytics')}>
              <span class="nav-icon">&#x1f4ca;</span> Analytics
            </button>
            <button class="nav-item ${this.currentView === 'leaderboard' ? 'active' : ''}"
              @click=${() => this._navigate('leaderboard')}>
              <span class="nav-icon">&#x1f3c6;</span> Leaderboard
            </button>
            ${this.isAdmin ? html`
              <button class="nav-item ${this.currentView === 'admin' ? 'active' : ''}"
                @click=${() => this._navigate('admin')}>
                <span class="nav-icon">&#x2699;</span> Admin
              </button>
            ` : ''}
          </nav>

          <!-- Main Content -->
          <main class="main">
            ${this.loading ? html`<div class="loading">Loading...</div>` : this._renderView()}
          </main>
        </div>

        <!-- FAB for new task -->
        ${this.currentView === 'tasks' ? html`
          <button class="fab" @click=${this._openNewTask} title="New Task">+</button>
        ` : ''}

        <!-- Bottom nav (mobile) -->
        <nav class="bottom-nav">
          <button class="bottom-nav-item ${this.currentView === 'tasks' ? 'active' : ''}"
            @click=${() => this._navigate('tasks')}>
            <span class="nav-icon">&#x2611;</span> Tasks
          </button>
          <button class="bottom-nav-item ${this.currentView === 'analytics' ? 'active' : ''}"
            @click=${() => this._navigate('analytics')}>
            <span class="nav-icon">&#x1f4ca;</span> Stats
          </button>
          <button class="bottom-nav-item ${this.currentView === 'leaderboard' ? 'active' : ''}"
            @click=${() => this._navigate('leaderboard')}>
            <span class="nav-icon">&#x1f3c6;</span> Board
          </button>
          ${this.isAdmin ? html`
            <button class="bottom-nav-item ${this.currentView === 'admin' ? 'active' : ''}"
              @click=${() => this._navigate('admin')}>
              <span class="nav-icon">&#x2699;</span> Admin
            </button>
          ` : ''}
        </nav>
      </div>
    `;
  }

  _renderView() {
    switch (this.currentView) {
      case 'tasks':
        return html`
          <task-list
            .tasks=${this.tasks}
            .labels=${this.labels}
            .currentUser=${this.currentUser}
            .users=${this.users}
            @task-selected=${this._openTaskDetail}
            @task-completed=${this._handleComplete}
            @refresh=${() => this._loadTasks()}
          ></task-list>
        `;
      case 'new-task':
        return html`
          <task-form
            .users=${this.users}
            .labels=${this.labels}
            .currentUser=${this.currentUser}
            @task-created=${this._backToList}
            @cancel=${this._backToList}
          ></task-form>
        `;
      case 'detail':
        return html`
          <task-detail
            .task=${this.selectedTask}
            .users=${this.users}
            .labels=${this.labels}
            .currentUser=${this.currentUser}
            @back=${this._backToList}
            @task-completed=${this._handleComplete}
            @task-updated=${() => this._loadTasks()}
          ></task-detail>
        `;
      case 'analytics':
        return html`
          <analytics-view
            .currentUser=${this.currentUser}
            .users=${this.users}
          ></analytics-view>
        `;
      case 'leaderboard':
        return html`
          <leaderboard-view></leaderboard-view>
        `;
      case 'admin':
        return html`
          <admin-panel
            .users=${this.users}
            .labels=${this.labels}
            .currentUser=${this.currentUser}
            @users-changed=${() => this._loadInitialData()}
            @labels-changed=${() => this._loadInitialData()}
          ></admin-panel>
        `;
      default:
        return html`<div>Unknown view</div>`;
    }
  }

  async _handleComplete(e) {
    const { taskId } = e.detail;
    if (!this.currentUser) return;
    try {
      await api.completeTask(taskId, this.currentUser.id);
      await this._loadTasks();
      await this._refreshUser();
    } catch (err) {
      this.error = err.message;
      setTimeout(() => { this.error = ''; }, 5000);
    }
  }
}

customElements.define('hacpm-app', HacpmApp);
