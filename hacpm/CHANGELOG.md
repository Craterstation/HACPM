# Changelog

## 0.1.1

- Fixed Docker build for Home Assistant base image compatibility
- Fixed startup script to use jq instead of bashio
- Added build dependencies for Python package compilation
- Switched to official Home Assistant base images

## 0.1.0

- Initial release
- Collaborative task management with family member support
- Natural language task creation (dateparser + custom parsing)
- Flexible scheduling: daily, weekly, monthly, yearly, specific days
- Due date vs completion date based recurrence
- Assignee rotation: round-robin, fewest-completed, random
- Nested subtasks with smart reset on recurring task completion
- Points and gamification system with leaderboard
- Completion restrictions (time-window enforcement)
- Time tracking with multi-session support
- Photo attachments (local storage)
- Labels and priority system
- Lit Web Components responsive dashboard
- Real-time sync via WebSockets
- Home Assistant integration: per-user to-do lists, native notifications
- Analytics with completion trends and per-user breakdowns
