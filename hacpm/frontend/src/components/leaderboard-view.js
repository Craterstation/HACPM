/**
 * Leaderboard View Component
 * Shows gamification leaderboard with points and task completion rankings.
 */

import { LitElement, html, css } from 'lit';
import { api } from '../services/api.js';

class LeaderboardView extends LitElement {
  static properties = {
    _leaderboard: { type: Array, state: true },
    _loading: { type: Boolean, state: true },
  };

  static styles = css`
    :host { display: block; }

    h2 { font-size: 20px; font-weight: 600; margin-bottom: 20px; }

    .leaderboard {
      background: var(--bg-card, #fff);
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 12px;
      overflow: hidden;
    }

    .leader-row {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 16px 20px;
      border-bottom: 1px solid var(--border-color, #e0e0e0);
      transition: background 0.15s;
    }
    .leader-row:last-child { border-bottom: none; }
    .leader-row:hover { background: var(--bg-primary, #fafafa); }

    .rank {
      width: 36px;
      height: 36px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 700;
      font-size: 16px;
      flex-shrink: 0;
    }
    .rank-1 { background: #ffd700; color: #7c6200; }
    .rank-2 { background: #c0c0c0; color: #555; }
    .rank-3 { background: #cd7f32; color: #fff; }
    .rank-default { background: var(--bg-primary, #fafafa); color: var(--text-secondary); }

    .leader-avatar {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      background: var(--primary-color, #03a9f4);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
      font-weight: 600;
      flex-shrink: 0;
    }

    .leader-info { flex: 1; }
    .leader-name { font-size: 16px; font-weight: 600; }
    .leader-meta {
      font-size: 13px;
      color: var(--text-secondary, #757575);
      margin-top: 2px;
    }

    .leader-points {
      font-size: 24px;
      font-weight: 700;
      color: var(--accent-color, #ff9800);
    }
    .leader-points span {
      font-size: 13px;
      font-weight: 400;
      color: var(--text-secondary, #757575);
    }

    .empty {
      text-align: center;
      padding: 60px;
      color: var(--text-secondary, #757575);
    }

    .loading { text-align: center; padding: 40px; color: var(--text-secondary); }

    /* Top 3 podium */
    .podium {
      display: flex;
      justify-content: center;
      align-items: flex-end;
      gap: 12px;
      margin-bottom: 24px;
      padding: 20px;
    }
    .podium-item {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
    }
    .podium-bar {
      width: 80px;
      border-radius: 8px 8px 0 0;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: flex-end;
      padding: 12px 8px;
      color: white;
      font-weight: 700;
    }
    .podium-1 { height: 120px; background: linear-gradient(#ffd700, #f0c000); color: #7c6200; }
    .podium-2 { height: 90px; background: linear-gradient(#d0d0d0, #b0b0b0); color: #555; }
    .podium-3 { height: 70px; background: linear-gradient(#cd7f32, #b07020); }
    .podium-name {
      font-size: 13px;
      font-weight: 600;
      text-align: center;
      max-width: 80px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--text-primary);
    }
    .podium-pts {
      font-size: 18px;
    }
  `;

  constructor() {
    super();
    this._leaderboard = [];
    this._loading = true;
  }

  async connectedCallback() {
    super.connectedCallback();
    await this._load();
  }

  async _load() {
    this._loading = true;
    try {
      this._leaderboard = await api.getLeaderboard(20);
    } catch { /* ignore */ }
    this._loading = false;
  }

  render() {
    if (this._loading) return html`<div class="loading">Loading leaderboard...</div>`;

    return html`
      <h2>Leaderboard</h2>

      ${this._leaderboard.length === 0 ? html`
        <div class="empty">
          <p>No completions yet. Start completing tasks to earn points!</p>
        </div>
      ` : html`
        <!-- Podium for top 3 -->
        ${this._leaderboard.length >= 3 ? this._renderPodium() : ''}

        <!-- Full list -->
        <div class="leaderboard">
          ${this._leaderboard.map((entry, i) => html`
            <div class="leader-row">
              <div class="rank ${i < 3 ? `rank-${i + 1}` : 'rank-default'}">${i + 1}</div>
              <div class="leader-avatar">${entry.avatar || entry.name?.[0] || '?'}</div>
              <div class="leader-info">
                <div class="leader-name">${entry.name}</div>
                <div class="leader-meta">${entry.tasks_completed} tasks completed</div>
              </div>
              <div class="leader-points">
                ${entry.total_points} <span>pts</span>
              </div>
            </div>
          `)}
        </div>
      `}
    `;
  }

  _renderPodium() {
    const top3 = this._leaderboard.slice(0, 3);
    // Display order: 2nd, 1st, 3rd
    const ordered = [top3[1], top3[0], top3[2]];

    return html`
      <div class="podium">
        ${ordered.map((entry, i) => {
          const actualRank = i === 0 ? 2 : i === 1 ? 1 : 3;
          return html`
            <div class="podium-item">
              <div class="podium-name">${entry.name}</div>
              <div class="podium-bar podium-${actualRank}">
                <div class="podium-pts">${entry.total_points}</div>
              </div>
            </div>
          `;
        })}
      </div>
    `;
  }
}

customElements.define('leaderboard-view', LeaderboardView);
