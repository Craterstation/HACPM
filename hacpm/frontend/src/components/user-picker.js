/**
 * User Picker Component
 * Displayed on startup to select which family member is using the device.
 */

import { LitElement, html, css } from 'lit';

class UserPicker extends LitElement {
  static properties = {
    users: { type: Array },
    pinInput: { type: String },
    selectedUser: { type: Object },
    error: { type: String },
  };

  static styles = css`
    :host {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      background: linear-gradient(135deg, #0288d1 0%, #03a9f4 50%, #4fc3f7 100%);
      padding: 20px;
    }

    .picker-card {
      background: white;
      border-radius: 16px;
      padding: 40px 32px;
      max-width: 480px;
      width: 100%;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      text-align: center;
    }

    h2 {
      color: #212121;
      margin-bottom: 8px;
      font-size: 24px;
    }
    .subtitle {
      color: #757575;
      margin-bottom: 32px;
      font-size: 14px;
    }

    .user-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .user-card {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      padding: 16px 8px;
      border-radius: 12px;
      cursor: pointer;
      transition: all 0.2s;
      border: 2px solid transparent;
      background: #f5f5f5;
    }
    .user-card:hover {
      background: #e3f2fd;
      border-color: #03a9f4;
    }
    .user-card.selected {
      background: #e3f2fd;
      border-color: #03a9f4;
    }

    .user-avatar {
      width: 56px;
      height: 56px;
      border-radius: 50%;
      background: #03a9f4;
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
      font-weight: 600;
    }
    .user-card.kid .user-avatar { background: #ff9800; }

    .user-name {
      font-size: 13px;
      font-weight: 500;
      color: #212121;
      word-break: break-word;
    }
    .user-role {
      font-size: 11px;
      color: #9e9e9e;
      text-transform: capitalize;
    }

    /* PIN entry */
    .pin-section {
      margin-top: 16px;
    }
    .pin-input {
      width: 120px;
      padding: 10px;
      text-align: center;
      font-size: 20px;
      letter-spacing: 8px;
      border: 2px solid #e0e0e0;
      border-radius: 8px;
      outline: none;
    }
    .pin-input:focus { border-color: #03a9f4; }

    .error { color: #f44336; font-size: 13px; margin-top: 8px; }

    .btn-primary {
      background: #03a9f4;
      color: white;
      border: none;
      padding: 10px 32px;
      border-radius: 8px;
      font-size: 15px;
      cursor: pointer;
      margin-top: 16px;
      font-family: inherit;
    }
    .btn-primary:hover { background: #0288d1; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

    .manage-link {
      display: inline-block;
      margin-top: 24px;
      color: #03a9f4;
      font-size: 13px;
      cursor: pointer;
      border: none;
      background: none;
      text-decoration: underline;
      font-family: inherit;
    }

    .empty-state {
      padding: 20px;
      color: #757575;
    }
  `;

  constructor() {
    super();
    this.users = [];
    this.pinInput = '';
    this.selectedUser = null;
    this.error = '';
  }

  render() {
    return html`
      <div class="picker-card">
        <h2>Welcome to HACPM</h2>
        <p class="subtitle">Who's using the device?</p>

        ${this.users.length === 0 ? html`
          <div class="empty-state">
            <p>No users yet. Set up your family members first!</p>
            <button class="btn-primary" @click=${() => this.dispatchEvent(new CustomEvent('manage-users'))}>
              Get Started
            </button>
          </div>
        ` : html`
          <div class="user-grid">
            ${this.users.map(user => html`
              <div
                class="user-card ${user.role} ${this.selectedUser?.id === user.id ? 'selected' : ''}"
                @click=${() => this._selectUser(user)}
              >
                <div class="user-avatar">${user.avatar || user.name?.[0] || '?'}</div>
                <div class="user-name">${user.name}</div>
                <div class="user-role">${user.role}</div>
              </div>
            `)}
          </div>

          ${this.selectedUser?.pin ? html`
            <div class="pin-section">
              <input
                class="pin-input"
                type="password"
                maxlength="6"
                placeholder="PIN"
                .value=${this.pinInput}
                @input=${(e) => { this.pinInput = e.target.value; }}
                @keyup=${(e) => { if (e.key === 'Enter') this._confirm(); }}
              >
              ${this.error ? html`<div class="error">${this.error}</div>` : ''}
            </div>
          ` : ''}

          <button
            class="btn-primary"
            ?disabled=${!this.selectedUser}
            @click=${this._confirm}
          >
            Continue
          </button>

          <button class="manage-link" @click=${() => this.dispatchEvent(new CustomEvent('manage-users'))}>
            Manage family members
          </button>
        `}
      </div>
    `;
  }

  _selectUser(user) {
    this.selectedUser = user;
    this.error = '';
    this.pinInput = '';
    // If no PIN required, don't wait
    if (!user.pin) {
      this.dispatchEvent(new CustomEvent('user-selected', { detail: { user } }));
    }
  }

  async _confirm() {
    if (!this.selectedUser) return;

    if (this.selectedUser.pin) {
      // Verify PIN
      try {
        const { api } = await import('../services/api.js');
        await api.verifyPin(this.selectedUser.id, this.pinInput);
        this.dispatchEvent(new CustomEvent('user-selected', { detail: { user: this.selectedUser } }));
      } catch {
        this.error = 'Invalid PIN';
      }
    } else {
      this.dispatchEvent(new CustomEvent('user-selected', { detail: { user: this.selectedUser } }));
    }
  }
}

customElements.define('user-picker', UserPicker);
