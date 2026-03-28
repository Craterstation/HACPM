# HACPM - Home Assistant Chores, Plants & Maintenance

A collaborative chore, plant care, and home maintenance tracker that runs as a Home Assistant add-on. Fully local, no cloud required.

---

## Setup Guide

### Prerequisites

- **Home Assistant OS** or **Home Assistant Supervised** (required for add-on support)
- Home Assistant version **2024.1** or newer
- Access to your HA instance via web browser

### Step 1: Add the Repository to Home Assistant

Since this is a custom add-on, you need to add the GitHub repository to your HA add-on store.

1. Open your Home Assistant UI
2. Go to **Settings** > **Add-ons** > **Add-on Store** (bottom right)
3. Click the **three dots menu** (top right) > **Repositories**
4. Paste the repository URL:
   ```
   https://github.com/craterstation/hacpm
   ```
5. Click **Add** > **Close**
6. The add-on store will refresh. Search for **"HACPM"** or scroll to find it

### Step 2: Install the Add-on

1. Click on **"HACPM - Home Assistant Chores, Plants & Maintenance"**
2. Click **Install** (this may take a few minutes to build the Docker image)
3. Once installed, you'll see the add-on info page

### Step 3: Configure the Add-on

On the add-on **Configuration** tab, you can adjust:

| Option | Default | Description |
|--------|---------|-------------|
| `log_level` | `info` | Logging verbosity: `debug`, `info`, `warning`, `error` |
| `realtime_sync` | `true` | Enable WebSocket real-time sync across devices |
| `default_points.low` | `1` | Points for low-priority tasks |
| `default_points.medium` | `3` | Points for medium-priority tasks |
| `default_points.high` | `5` | Points for high-priority tasks |
| `default_points.critical` | `10` | Points for critical-priority tasks |

### Step 4: Start the Add-on

1. Go to the **Info** tab
2. Toggle **"Show in sidebar"** to ON (recommended)
3. Click **Start**
4. Wait for the log to show `"HACPM is ready!"`
5. Click **"Open Web UI"** or use the sidebar link

### Step 5: Initial Setup (First Run)

On first launch, you'll be directed to the Admin panel:

1. **Create Family Members**
   - Click **Admin** > **Family Members** tab
   - Add each family member with:
     - **Name**: Internal identifier (e.g., `john`)
     - **Display Name**: What's shown in the UI (e.g., `John`)
     - **Role**: `Parent` (admin access) or `Kid` (limited)
     - **PIN** (optional): Simple PIN for kid accounts to prevent unauthorized access

2. **Create Labels**
   - Go to **Admin** > **Labels** tab
   - Add categories like: `Kitchen`, `Bathroom`, `Yard`, `Plants`, `Pets`, etc.
   - Each label gets a color for visual organization

3. **Start Creating Tasks!**

---

## How to Use

### Creating Tasks

**Smart Input (NLP mode):**
- Click the **+** button
- Type naturally: `"Water the plants every 3 days"`
- HACPM automatically detects:
  - Task title
  - Due dates and times
  - Recurrence patterns
- Assign to family members and add labels

**Supported NLP patterns:**
- `"Take the trash out every Monday and Tuesday at 6:15 pm"`
- `"Change water filter every 6 months"`
- `"Pay rent on the 1st of every month"`
- `"Clean gutters twice a year in March and September"`
- `"Mow the lawn weekly"`

**Manual mode:**
- Switch to **Manual** tab for full control over all fields
- Set priority, custom points, recurrence rules, completion restrictions, etc.

### Task Completion

- Tap the **circle** next to a task to mark it complete
- For **recurring tasks**: the task automatically resets with a new due date, and all subtasks reset too
- Points are awarded to whoever completes the task

### Completion Restrictions

Set a completion window (e.g., "last 4 hours before due") to prevent tasks from being marked done too early. The complete button will be disabled until the window opens.

### Subtasks

- Open a task > click **"+ Add Subtask"**
- Subtasks can be nested (subtask within a subtask)
- For recurring tasks, **all subtasks automatically reset** when the parent is completed

### Assignee Rotation

When a task has multiple assignees, enable rotation:
- **Round Robin**: Takes turns in order
- **Fewest Completed**: Assigns to whoever has done the least
- **Random**: Random pick each time

### Time Tracking

- Open a task > click **"Start Timer"**
- Click **"Stop Timer"** when done
- Track time across multiple sessions per task

### Photos

- Open a task > scroll to **Photos**
- Click the **+** to upload images directly from your device
- Photos are stored locally on your HA instance

### Analytics

- View overall completion rates, tasks by priority/label
- **Completion Trend**: See a 30-day chart of completed tasks
- **Per-User Stats**: Points, completions, time tracked per person

### Leaderboard

- Gamified leaderboard showing points and task completion rankings
- Top 3 displayed on a podium
- Motivates kids (and parents!) to stay on top of chores

---

## Home Assistant Integration

### To-Do Lists

HACPM automatically creates a **separate HA to-do list for each user**:
- `todo.hacpm_john`
- `todo.hacpm_jane`
- etc.

These appear natively in HA and can be used in automations, dashboards, and Lovelace cards.

### Notifications

HACPM uses HA's native **persistent notifications** and can target specific devices:
- Task due reminders
- Completion notifications (with points earned)
- New assignment notifications

To set up mobile notifications, configure the HA Companion App on your phone.

### Automations

You can create HA automations that interact with HACPM's to-do lists:

```yaml
# Example: Send a reminder when tasks are overdue
automation:
  - alias: "HACPM Overdue Reminder"
    trigger:
      - platform: time
        at: "09:00:00"
    action:
      - service: persistent_notification.create
        data:
          title: "Chore Reminder"
          message: "Check your HACPM tasks!"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│          Home Assistant OS              │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │       HACPM Add-on (Docker)       │  │
│  │                                   │  │
│  │  ┌─────────┐   ┌──────────────┐  │  │
│  │  │ FastAPI  │   │  Lit Web UI  │  │  │
│  │  │ Backend  │◄─►│  (Ingress)   │  │  │
│  │  └────┬─────┘   └──────────────┘  │  │
│  │       │                           │  │
│  │  ┌────▼─────┐   ┌──────────────┐  │  │
│  │  │  SQLite  │   │  WebSocket   │  │  │
│  │  │    DB    │   │  Real-time   │  │  │
│  │  └──────────┘   └──────────────┘  │  │
│  └───────────┬───────────────────────┘  │
│              │ Supervisor API           │
│  ┌───────────▼───────────────────────┐  │
│  │  HA Core                          │  │
│  │  - To-Do Lists (per user)         │  │
│  │  - Notifications                  │  │
│  │  - Automations                    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python 3 + FastAPI |
| Database | SQLite (persistent in `/data/`) |
| Frontend | Lit Web Components |
| Real-time | WebSockets |
| NLP | dateparser + custom regex |
| Container | Docker (HA add-on base image) |

---

## Data & Storage

All data is stored locally:
- **Database**: `/data/db/hacpm.sqlite` (persisted across add-on restarts)
- **Photos**: `/data/photos/` (persisted)
- Both directories are mapped to HA's persistent storage

### Backup

Your HACPM data is included in HA's built-in backup system. When you create a backup in HA (Settings > System > Backups), the add-on data is automatically included.

---

## API Reference

HACPM exposes a REST API accessible from within the add-on's ingress URL. Full auto-generated API docs are available at:

```
<your-ha-url>/api/hacpm/docs
```

Key endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/tasks/` | List all tasks (with filters) |
| POST | `/api/tasks/` | Create a task |
| POST | `/api/tasks/nlp` | Create task from natural language |
| POST | `/api/tasks/{id}/complete` | Complete a task |
| GET | `/api/users/` | List all users |
| GET | `/api/analytics/overview` | Get overview stats |
| GET | `/api/analytics/leaderboard` | Get points leaderboard |
| WS | `/ws` | WebSocket for real-time updates |

---

## Troubleshooting

### Add-on won't start
- Check the **Log** tab for error messages
- Ensure your HA instance has enough memory (minimum 512MB free)
- Try restarting the add-on

### Tasks not syncing to HA to-do lists
- Ensure the add-on has **Home Assistant API** access enabled (it should be by default)
- Check that the Supervisor token is available (automatic in add-on mode)

### WebSocket connection drops
- This is normal on unstable networks; the client auto-reconnects
- Check your browser's developer console for connection errors

### Photos not uploading
- Maximum file size depends on available disk space
- Supported formats: JPEG, PNG, GIF, WebP
- Ensure `/data/photos/` directory is writable

---

## Future Enhancements (Roadmap)

- [ ] NFC tag support for quick task completion
- [ ] Custom dashboard cards for HA Lovelace
- [ ] Import/export tasks (CSV, JSON)
- [ ] Task templates and presets
- [ ] Multi-language support
- [ ] Dark mode auto-detection
- [ ] Calendar view integration
- [ ] Voice assistant integration (Assist)
