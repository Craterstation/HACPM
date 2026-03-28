/**
 * Admin Panel Component
 * Manage users, labels, and system settings. Only visible to parent role.
 */

import { LitElement, html, css } from 'lit';
import { api } from '../services/api.js';

class AdminPanel extends LitElement {
  static properties = {
    users: { type: Array },
    labels: { type: Array },
    currentUser: { type: Object },
    _tab: { type: String, state: true },
    // User form
    _userName: { type: String, state: true },
    _userDisplayName: { type: String, state: true },
    _userRole: { type: String, state: true },
    _userPin: { type: String, state: true },
    _editingUserId: { type: Number, state: true },
    // Label form
    _labelName: { type: String, state: true },
    _labelColor: { type: String, state: true },
    _labelIcon: { type: String, state: true },
    _editingLabelId: { type: Number, state: true },
    _error: { type: String, state: true },
  };

  static styles = css`
    :host { display: block; }

    h2 { font-size: 20px; font-weight: 600; margin-bottom: 20px; }

    .tabs {
      display: flex;
      gap: 0;
      border-bottom: 2px solid var(--border-color, #e0e0e0);
      margin-bottom: 20px;
    }
    .tab {
      padding: 10px 20px;
      border: none;
      background: none;
      cursor: pointer;
      font-size: 14px;
      font-family: inherit;
      color: var(--text-secondary, #757575);
      border-bottom: 2px solid transparent;
      margin-bottom: -2px;
    }
    .tab.active {
      color: var(--primary-color, #03a9f4);
      border-bottom-color: var(--primary-color, #03a9f4);
      font-weight: 500;
    }

    .panel {
      background: var(--bg-card, #fff);
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 10px;
      padding: 20px;
    }

    .form-row {
      display: flex;
      gap: 10px;
      margin-bottom: 12px;
      flex-wrap: wrap;
      align-items: flex-end;
    }
    .form-field {
      display: flex;
      flex-direction: column;
      gap: 4px;
    }
    .form-field label {
      font-size: 12px;
      color: var(--text-secondary, #757575);
      font-weight: 500;
    }
    .form-field input, .form-field select {
      padding: 8px 10px;
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 6px;
      font-size: 13px;
      font-family: inherit;
      outline: none;
    }
    .form-field input:focus, .form-field select:focus {
      border-color: var(--primary-color, #03a9f4);
    }

    .btn {
      padding: 8px 16px;
      border-radius: 6px;
      font-size: 13px;
      cursor: pointer;
      border: none;
      font-family: inherit;
      font-weight: 500;
    }
    .btn-primary { background: var(--primary-color, #03a9f4); color: white; }
    .btn-primary:hover { background: #0288d1; }
    .btn-danger { background: var(--error-color, #f44336); color: white; }
    .btn-secondary {
      background: var(--bg-primary, #fafafa);
      border: 1px solid var(--border-color, #e0e0e0);
      color: var(--text-primary);
    }

    /* Item list */
    .item-list { margin-top: 16px; }
    .item-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 0;
      border-bottom: 1px solid var(--border-color, #e0e0e0);
    }
    .item-info {
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .item-avatar {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      background: var(--primary-color, #03a9f4);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 600;
    }
    .item-avatar.kid { background: #ff9800; }
    .item-name { font-weight: 500; font-size: 14px; }
    .item-meta { font-size: 12px; color: var(--text-secondary, #757575); }
    .item-actions { display: flex; gap: 6px; }

    .color-swatch {
      width: 24px;
      height: 24px;
      border-radius: 50%;
      border: 2px solid var(--border-color, #e0e0e0);
    }
    .color-input {
      width: 60px;
      padding: 2px;
    }

    .error { color: var(--error-color, #f44336); font-size: 13px; margin-top: 8px; }
  `;

  constructor() {
    super();
    this._tab = 'users';
    this._resetUserForm();
    this._resetLabelForm();
    this._error = '';
  }

  _resetUserForm() {
    this._userName = '';
    this._userDisplayName = '';
    this._userRole = 'kid';
    this._userPin = '';
    this._editingUserId = null;
  }

  _resetLabelForm() {
    this._labelName = '';
    this._labelColor = '#3B82F6';
    this._labelIcon = '';
    this._editingLabelId = null;
  }

  render() {
    return html`
      <h2>Admin Panel</h2>

      <div class="tabs">
        <button class="tab ${this._tab === 'users' ? 'active' : ''}"
          @click=${() => { this._tab = 'users'; }}>Family Members</button>
        <button class="tab ${this._tab === 'labels' ? 'active' : ''}"
          @click=${() => { this._tab = 'labels'; }}>Labels</button>
      </div>

      <div class="panel">
        ${this._tab === 'users' ? this._renderUsersTab() : this._renderLabelsTab()}
        ${this._error ? html`<div class="error">${this._error}</div>` : ''}
      </div>
    `;
  }

  _renderUsersTab() {
    return html`
      <div class="form-row">
        <div class="form-field">
          <label>Name</label>
          <input type="text" .value=${this._userName}
            @input=${(e) => { this._userName = e.target.value; }}
            placeholder="e.g., john">
        </div>
        <div class="form-field">
          <label>Display Name</label>
          <input type="text" .value=${this._userDisplayName}
            @input=${(e) => { this._userDisplayName = e.target.value; }}
            placeholder="e.g., John">
        </div>
        <div class="form-field">
          <label>Role</label>
          <select .value=${this._userRole} @change=${(e) => { this._userRole = e.target.value; }}>
            <option value="parent">Parent (Admin)</option>
            <option value="kid">Kid</option>
          </select>
        </div>
        <div class="form-field">
          <label>PIN (optional)</label>
          <input type="text" maxlength="6" .value=${this._userPin}
            @input=${(e) => { this._userPin = e.target.value; }}
            placeholder="1234">
        </div>
        <button class="btn btn-primary" @click=${this._saveUser}>
          ${this._editingUserId ? 'Update' : 'Add'} User
        </button>
        ${this._editingUserId ? html`
          <button class="btn btn-secondary" @click=${() => this._resetUserForm()}>Cancel</button>
        ` : ''}
      </div>

      <div class="item-list">
        ${this.users.map(user => html`
          <div class="item-row">
            <div class="item-info">
              <div class="item-avatar ${user.role}">${user.name?.[0] || '?'}</div>
              <div>
                <div class="item-name">${user.display_name || user.name}</div>
                <div class="item-meta">${user.role} ${user.pin ? '(PIN set)' : ''} &middot; ${user.total_points || 0} pts</div>
              </div>
            </div>
            <div class="item-actions">
              <button class="btn btn-secondary" @click=${() => this._editUser(user)}>Edit</button>
              <button class="btn btn-danger" @click=${() => this._deleteUser(user.id)}>Remove</button>
            </div>
          </div>
        `)}
      </div>
    `;
  }

  _renderLabelsTab() {
    return html`
      <div class="form-row">
        <div class="form-field">
          <label>Label Name</label>
          <input type="text" .value=${this._labelName}
            @input=${(e) => { this._labelName = e.target.value; }}
            placeholder="e.g., Kitchen">
        </div>
        <div class="form-field">
          <label>Color</label>
          <input type="color" class="color-input" .value=${this._labelColor}
            @input=${(e) => { this._labelColor = e.target.value; }}>
        </div>
        <div class="form-field">
          <label>Icon (MDI name)</label>
          <input type="text" .value=${this._labelIcon}
            @input=${(e) => { this._labelIcon = e.target.value; }}
            placeholder="e.g., mdi:broom">
        </div>
        <button class="btn btn-primary" @click=${this._saveLabel}>
          ${this._editingLabelId ? 'Update' : 'Add'} Label
        </button>
        ${this._editingLabelId ? html`
          <button class="btn btn-secondary" @click=${() => this._resetLabelForm()}>Cancel</button>
        ` : ''}
      </div>

      <div class="item-list">
        ${this.labels.map(label => html`
          <div class="item-row">
            <div class="item-info">
              <div class="color-swatch" style="background:${label.color}"></div>
              <div>
                <div class="item-name">${label.name}</div>
                <div class="item-meta">${label.icon || 'No icon'}</div>
              </div>
            </div>
            <div class="item-actions">
              <button class="btn btn-secondary" @click=${() => this._editLabel(label)}>Edit</button>
              <button class="btn btn-danger" @click=${() => this._deleteLabel(label.id)}>Delete</button>
            </div>
          </div>
        `)}
      </div>
    `;
  }

  // ── User CRUD ──
  _editUser(user) {
    this._editingUserId = user.id;
    this._userName = user.name;
    this._userDisplayName = user.display_name || '';
    this._userRole = user.role;
    this._userPin = user.pin || '';
  }

  async _saveUser() {
    if (!this._userName.trim()) {
      this._error = 'Name is required';
      return;
    }
    this._error = '';
    try {
      const data = {
        name: this._userName,
        display_name: this._userDisplayName || null,
        role: this._userRole,
        pin: this._userPin || null,
      };
      if (this._editingUserId) {
        await api.updateUser(this._editingUserId, data);
      } else {
        await api.createUser(data);
      }
      this._resetUserForm();
      this.dispatchEvent(new CustomEvent('users-changed'));
    } catch (e) {
      this._error = e.message;
    }
  }

  async _deleteUser(id) {
    if (!confirm('Remove this user? They will be deactivated.')) return;
    try {
      await api.deleteUser(id);
      this.dispatchEvent(new CustomEvent('users-changed'));
    } catch (e) {
      this._error = e.message;
    }
  }

  // ── Label CRUD ──
  _editLabel(label) {
    this._editingLabelId = label.id;
    this._labelName = label.name;
    this._labelColor = label.color;
    this._labelIcon = label.icon || '';
  }

  async _saveLabel() {
    if (!this._labelName.trim()) {
      this._error = 'Label name is required';
      return;
    }
    this._error = '';
    try {
      const data = {
        name: this._labelName,
        color: this._labelColor,
        icon: this._labelIcon || null,
      };
      if (this._editingLabelId) {
        await api.updateLabel(this._editingLabelId, data);
      } else {
        await api.createLabel(data);
      }
      this._resetLabelForm();
      this.dispatchEvent(new CustomEvent('labels-changed'));
    } catch (e) {
      this._error = e.message;
    }
  }

  async _deleteLabel(id) {
    if (!confirm('Delete this label?')) return;
    try {
      await api.deleteLabel(id);
      this.dispatchEvent(new CustomEvent('labels-changed'));
    } catch (e) {
      this._error = e.message;
    }
  }
}

customElements.define('admin-panel', AdminPanel);
