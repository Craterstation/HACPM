/**
 * Task Form Component
 * Create new tasks with NLP or manual input.
 */

import { LitElement, html, css } from 'lit';
import { api } from '../services/api.js';

class TaskForm extends LitElement {
  static properties = {
    users: { type: Array },
    labels: { type: Array },
    currentUser: { type: Object },
    mode: { type: String },         // 'nlp' or 'manual'
    nlpText: { type: String },
    nlpPreview: { type: Object },
    // Manual form fields
    title: { type: String },
    description: { type: String },
    priority: { type: String },
    dueDate: { type: String },
    dueTime: { type: String },
    points: { type: String },
    recurrenceRule: { type: String },
    recurrenceMode: { type: String },
    completionRestriction: { type: String },
    selectedAssignees: { type: Array },
    selectedLabels: { type: Array },
    parentTaskId: { type: Number },
    // Rotation
    enableRotation: { type: Boolean },
    rotationType: { type: String },
    rotationParticipants: { type: Array },
    // State
    submitting: { type: Boolean },
    error: { type: String },
  };

  static styles = css`
    :host { display: block; }

    .form-card {
      background: var(--bg-card, #fff);
      border-radius: 12px;
      padding: 24px;
      border: 1px solid var(--border-color, #e0e0e0);
    }

    .form-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }
    .form-header h2 { font-size: 20px; font-weight: 600; }

    .mode-toggle {
      display: flex;
      gap: 0;
      border-radius: 8px;
      overflow: hidden;
      border: 1px solid var(--border-color, #e0e0e0);
    }
    .mode-btn {
      padding: 6px 16px;
      border: none;
      background: var(--bg-primary, #fafafa);
      cursor: pointer;
      font-size: 13px;
      font-family: inherit;
      color: var(--text-secondary, #757575);
    }
    .mode-btn.active {
      background: var(--primary-color, #03a9f4);
      color: white;
    }

    /* NLP Mode */
    .nlp-input {
      width: 100%;
      padding: 14px;
      font-size: 16px;
      border: 2px solid var(--border-color, #e0e0e0);
      border-radius: 10px;
      outline: none;
      font-family: inherit;
      background: var(--bg-primary, #fafafa);
      color: var(--text-primary, #212121);
    }
    .nlp-input:focus { border-color: var(--primary-color, #03a9f4); }
    .nlp-hint {
      font-size: 12px;
      color: var(--text-secondary, #757575);
      margin-top: 8px;
    }

    .nlp-preview {
      background: #e8f5e9;
      border-radius: 8px;
      padding: 12px;
      margin-top: 12px;
      font-size: 13px;
    }
    .nlp-preview .label { font-weight: 600; color: #2e7d32; }

    /* Form fields */
    .field {
      margin-bottom: 16px;
    }
    .field label {
      display: block;
      font-size: 13px;
      font-weight: 500;
      margin-bottom: 6px;
      color: var(--text-secondary, #757575);
    }
    .field input, .field textarea, .field select {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid var(--border-color, #e0e0e0);
      border-radius: 8px;
      font-size: 14px;
      outline: none;
      font-family: inherit;
      background: var(--bg-primary, #fafafa);
      color: var(--text-primary, #212121);
    }
    .field input:focus, .field textarea:focus, .field select:focus {
      border-color: var(--primary-color, #03a9f4);
    }
    .field textarea { min-height: 80px; resize: vertical; }

    .field-row {
      display: flex;
      gap: 12px;
    }
    .field-row .field { flex: 1; }

    /* Multi-select chips */
    .chip-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .chip {
      padding: 4px 12px;
      border-radius: 16px;
      font-size: 13px;
      cursor: pointer;
      border: 1px solid var(--border-color, #e0e0e0);
      background: var(--bg-primary, #fafafa);
      transition: all 0.15s;
      font-family: inherit;
      color: var(--text-primary, #212121);
    }
    .chip.selected {
      background: var(--primary-color, #03a9f4);
      color: white;
      border-color: var(--primary-color, #03a9f4);
    }
    .chip:hover { border-color: var(--primary-color, #03a9f4); }

    /* Schedule presets */
    .schedule-presets {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-bottom: 8px;
    }
    .preset-btn {
      padding: 4px 10px;
      border-radius: 14px;
      font-size: 12px;
      border: 1px solid var(--border-color, #e0e0e0);
      background: var(--bg-primary, #fafafa);
      cursor: pointer;
      font-family: inherit;
      color: var(--text-primary, #212121);
    }
    .preset-btn:hover { border-color: var(--primary-color, #03a9f4); }
    .preset-btn.active {
      background: #e3f2fd;
      border-color: var(--primary-color, #03a9f4);
      color: var(--primary-color, #03a9f4);
    }

    /* Buttons */
    .actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
      margin-top: 24px;
    }
    .btn {
      padding: 10px 24px;
      border-radius: 8px;
      font-size: 14px;
      cursor: pointer;
      border: none;
      font-family: inherit;
      font-weight: 500;
    }
    .btn-primary {
      background: var(--primary-color, #03a9f4);
      color: white;
    }
    .btn-primary:hover { background: var(--primary-dark, #0288d1); }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: var(--bg-primary, #fafafa);
      color: var(--text-primary, #212121);
      border: 1px solid var(--border-color, #e0e0e0);
    }

    .error { color: var(--error-color, #f44336); font-size: 13px; margin-top: 8px; }

    .section-title {
      font-size: 14px;
      font-weight: 600;
      margin-top: 20px;
      margin-bottom: 10px;
      color: var(--text-primary, #212121);
    }
  `;

  constructor() {
    super();
    this.users = [];
    this.labels = [];
    this.currentUser = null;
    this.mode = 'nlp';
    this.nlpText = '';
    this.nlpPreview = null;
    this.title = '';
    this.description = '';
    this.priority = 'medium';
    this.dueDate = '';
    this.dueTime = '';
    this.points = '';
    this.recurrenceRule = '';
    this.recurrenceMode = 'due_date';
    this.completionRestriction = '';
    this.selectedAssignees = [];
    this.selectedLabels = [];
    this.parentTaskId = null;
    this.enableRotation = false;
    this.rotationType = 'round_robin';
    this.rotationParticipants = [];
    this.submitting = false;
    this.error = '';
  }

  render() {
    return html`
      <div class="form-card">
        <div class="form-header">
          <h2>New Task</h2>
          <div class="mode-toggle">
            <button class="mode-btn ${this.mode === 'nlp' ? 'active' : ''}" @click=${() => { this.mode = 'nlp'; }}>
              Smart Input
            </button>
            <button class="mode-btn ${this.mode === 'manual' ? 'active' : ''}" @click=${() => { this.mode = 'manual'; }}>
              Manual
            </button>
          </div>
        </div>

        ${this.mode === 'nlp' ? this._renderNLPMode() : this._renderManualMode()}

        <!-- Common: Assignees & Labels -->
        <div class="section-title">Assign To</div>
        <div class="chip-list">
          ${this.users.map(u => html`
            <button
              class="chip ${this.selectedAssignees.includes(u.id) ? 'selected' : ''}"
              @click=${() => this._toggleAssignee(u.id)}
            >
              ${u.display_name || u.name}
            </button>
          `)}
        </div>

        ${this.selectedAssignees.length > 1 ? html`
          <div style="margin-top: 12px;">
            <label>
              <input type="checkbox" .checked=${this.enableRotation}
                @change=${(e) => { this.enableRotation = e.target.checked; }}>
              Enable assignee rotation
            </label>
            ${this.enableRotation ? html`
              <select style="margin-top: 6px; padding: 6px;" @change=${(e) => { this.rotationType = e.target.value; }}>
                <option value="round_robin">Round Robin (take turns)</option>
                <option value="fewest_completed">Fewest Completed First</option>
                <option value="random">Random</option>
              </select>
            ` : ''}
          </div>
        ` : ''}

        <div class="section-title">Labels</div>
        <div class="chip-list">
          ${this.labels.map(l => html`
            <button
              class="chip ${this.selectedLabels.includes(l.id) ? 'selected' : ''}"
              style="${this.selectedLabels.includes(l.id) ? `background:${l.color};border-color:${l.color}` : ''}"
              @click=${() => this._toggleLabel(l.id)}
            >
              ${l.name}
            </button>
          `)}
        </div>

        ${this.error ? html`<div class="error">${this.error}</div>` : ''}

        <div class="actions">
          <button class="btn btn-secondary" @click=${() => this.dispatchEvent(new CustomEvent('cancel'))}>
            Cancel
          </button>
          <button class="btn btn-primary" ?disabled=${this.submitting} @click=${this._submit}>
            ${this.submitting ? 'Creating...' : 'Create Task'}
          </button>
        </div>
      </div>
    `;
  }

  _renderNLPMode() {
    return html`
      <div class="field">
        <input
          class="nlp-input"
          type="text"
          placeholder="e.g., Take the trash out every Monday and Tuesday at 6:15 pm"
          .value=${this.nlpText}
          @input=${this._onNLPInput}
          @keyup=${(e) => { if (e.key === 'Enter') this._submit(); }}
        >
        <div class="nlp-hint">
          Describe the task in plain English. Dates, times, and recurrence will be automatically detected.
        </div>
      </div>

      ${this.nlpPreview ? html`
        <div class="nlp-preview">
          <div><span class="label">Task:</span> ${this.nlpPreview.title}</div>
          ${this.nlpPreview.due_date ? html`<div><span class="label">Due:</span> ${new Date(this.nlpPreview.due_date).toLocaleString()}</div>` : ''}
          ${this.nlpPreview.recurrence_description ? html`<div><span class="label">Repeats:</span> ${this.nlpPreview.recurrence_description}</div>` : ''}
          <div><span class="label">Confidence:</span> ${Math.round(this.nlpPreview.confidence * 100)}%</div>
        </div>
      ` : ''}
    `;
  }

  _renderManualMode() {
    return html`
      <div class="field">
        <label>Task Title</label>
        <input type="text" .value=${this.title} @input=${(e) => { this.title = e.target.value; }}
          placeholder="What needs to be done?">
      </div>

      <div class="field">
        <label>Description (optional)</label>
        <textarea .value=${this.description} @input=${(e) => { this.description = e.target.value; }}
          placeholder="Add details..."></textarea>
      </div>

      <div class="field-row">
        <div class="field">
          <label>Priority</label>
          <select .value=${this.priority} @change=${(e) => { this.priority = e.target.value; }}>
            <option value="low">Low (1 pt)</option>
            <option value="medium" selected>Medium (3 pts)</option>
            <option value="high">High (5 pts)</option>
            <option value="critical">Critical (10 pts)</option>
          </select>
        </div>
        <div class="field">
          <label>Custom Points (optional)</label>
          <input type="number" min="0" .value=${this.points}
            @input=${(e) => { this.points = e.target.value; }}
            placeholder="Override priority points">
        </div>
      </div>

      <div class="field-row">
        <div class="field">
          <label>Due Date</label>
          <input type="date" .value=${this.dueDate} @input=${(e) => { this.dueDate = e.target.value; }}>
        </div>
        <div class="field">
          <label>Due Time</label>
          <input type="time" .value=${this.dueTime} @input=${(e) => { this.dueTime = e.target.value; }}>
        </div>
      </div>

      <!-- Recurrence -->
      <div class="section-title">Repeat Schedule</div>
      <div class="schedule-presets">
        ${[
          { label: 'None', value: '' },
          { label: 'Daily', value: 'FREQ=DAILY' },
          { label: 'Weekly', value: 'FREQ=WEEKLY' },
          { label: 'Monthly', value: 'FREQ=MONTHLY' },
          { label: 'Yearly', value: 'FREQ=YEARLY' },
        ].map(p => html`
          <button class="preset-btn ${this.recurrenceRule === p.value ? 'active' : ''}"
            @click=${() => { this.recurrenceRule = p.value; }}>
            ${p.label}
          </button>
        `)}
      </div>

      ${this.recurrenceRule ? html`
        <div class="field">
          <label>Custom RRULE (advanced)</label>
          <input type="text" .value=${this.recurrenceRule}
            @input=${(e) => { this.recurrenceRule = e.target.value; }}
            placeholder="e.g., FREQ=WEEKLY;BYDAY=MO,WE,FR">
        </div>
        <div class="field-row">
          <div class="field">
            <label>Recurrence Based On</label>
            <select .value=${this.recurrenceMode} @change=${(e) => { this.recurrenceMode = e.target.value; }}>
              <option value="due_date">Due Date (consistent cadence)</option>
              <option value="completion_date">Completion Date (flexible)</option>
            </select>
          </div>
          <div class="field">
            <label>Completion Window (hours)</label>
            <input type="number" min="0" .value=${this.completionRestriction}
              @input=${(e) => { this.completionRestriction = e.target.value; }}
              placeholder="e.g., 4 = last 4 hours only">
          </div>
        </div>
      ` : ''}
    `;
  }

  async _onNLPInput(e) {
    this.nlpText = e.target.value;
    // Debounced preview
    clearTimeout(this._nlpTimer);
    if (this.nlpText.length > 5) {
      this._nlpTimer = setTimeout(async () => {
        try {
          this.nlpPreview = await api.parseNLP(this.nlpText);
        } catch { /* ignore preview errors */ }
      }, 500);
    } else {
      this.nlpPreview = null;
    }
  }

  _toggleAssignee(id) {
    if (this.selectedAssignees.includes(id)) {
      this.selectedAssignees = this.selectedAssignees.filter(x => x !== id);
    } else {
      this.selectedAssignees = [...this.selectedAssignees, id];
    }
  }

  _toggleLabel(id) {
    if (this.selectedLabels.includes(id)) {
      this.selectedLabels = this.selectedLabels.filter(x => x !== id);
    } else {
      this.selectedLabels = [...this.selectedLabels, id];
    }
  }

  async _submit() {
    this.error = '';
    this.submitting = true;

    try {
      if (this.mode === 'nlp') {
        if (!this.nlpText.trim()) {
          this.error = 'Please describe the task';
          this.submitting = false;
          return;
        }
        await api.createTaskFromNLP(
          this.nlpText,
          this.currentUser?.id,
          this.selectedAssignees,
          this.selectedLabels,
        );
      } else {
        if (!this.title.trim()) {
          this.error = 'Task title is required';
          this.submitting = false;
          return;
        }

        let dueDate = null;
        if (this.dueDate) {
          dueDate = this.dueTime
            ? `${this.dueDate}T${this.dueTime}:00`
            : `${this.dueDate}T00:00:00`;
        }

        const taskData = {
          title: this.title,
          description: this.description || null,
          priority: this.priority,
          points: this.points ? parseInt(this.points) : null,
          due_date: dueDate,
          recurrence_rule: this.recurrenceRule || null,
          recurrence_mode: this.recurrenceRule ? this.recurrenceMode : null,
          completion_restriction_hours: this.completionRestriction ? parseInt(this.completionRestriction) : null,
          parent_task_id: this.parentTaskId,
          created_by: this.currentUser?.id,
          assignee_ids: this.selectedAssignees,
          label_ids: this.selectedLabels,
        };

        // Add rotation if enabled
        if (this.enableRotation && this.selectedAssignees.length > 1) {
          taskData.rotation = {
            rotation_type: this.rotationType,
            participant_ids: this.selectedAssignees,
          };
        }

        await api.createTask(taskData);
      }

      this.dispatchEvent(new CustomEvent('task-created'));
    } catch (e) {
      this.error = e.message;
    } finally {
      this.submitting = false;
    }
  }
}

customElements.define('task-form', TaskForm);
