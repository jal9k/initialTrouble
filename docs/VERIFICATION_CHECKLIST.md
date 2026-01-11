# TechTim(e) Desktop Application - Verification Checklist

Use this checklist to verify the desktop application is ready for release.

## Development Environment

- [ ] `pip install -e ".[all]"` completes without errors
- [ ] `cd frontend/techtime && npm install` completes without errors
- [ ] `pytest` passes all tests
- [ ] `ruff check .` passes without errors (or expected warnings only)

## Development Mode

- [ ] `npm run dev` starts frontend on http://localhost:3000
- [ ] `python desktop_main.py --dev` opens window loading from dev server
- [ ] Frontend hot reload works (change code, see update)
- [ ] Chrome DevTools accessible (right-click → Inspect)

## Static Build Mode

- [ ] `npm run build` creates `frontend/techtime/out/index.html`
- [ ] `python desktop_main.py` loads from static files
- [ ] All pages render correctly

## Desktop Application Features

### Startup
- [ ] Loading screen shows during initialization
- [ ] Progress bar updates during model download (if needed)
- [ ] Error messages display properly if startup fails
- [ ] Application reaches ready state

### Chat
- [ ] Can start new conversation
- [ ] Messages send and receive
- [ ] Tool calls display in UI
- [ ] Tool results show success/failure
- [ ] Streaming responses work
- [ ] Conversation history persists after restart

### Sessions
- [ ] Session list shows in sidebar
- [ ] Can switch between sessions
- [ ] Can delete sessions
- [ ] Session preview shows first message

### Tools
- [ ] Manual tool panel lists all tools
- [ ] Can execute tools manually
- [ ] Tool results display correctly

### Analytics
- [ ] Analytics dashboard shows data
- [ ] Session counts are accurate
- [ ] Tool statistics display

### Preferences
- [ ] Theme selection persists
- [ ] Window position saves on close
- [ ] Window opens at saved position

## Build Process

- [ ] `python scripts/download_ollama.py` downloads binaries
- [ ] `python scripts/build_frontend.py` builds frontend
- [ ] `python scripts/build_app.py` completes without errors
- [ ] `dist/TechTime/` (or `.app`) is created

## Bundled Application

### macOS
- [ ] `dist/TechTime.app` launches
- [ ] Ollama starts automatically
- [ ] Model downloads if needed
- [ ] Chat works
- [ ] No console window appears

### Windows
- [ ] `dist/TechTime/TechTime.exe` launches
- [ ] Ollama starts automatically
- [ ] Model downloads if needed
- [ ] Chat works
- [ ] No console window appears

## Edge Cases

- [ ] Handles Ollama not found gracefully
- [ ] Handles model not available gracefully
- [ ] Handles network errors gracefully
- [ ] Clean shutdown (no orphaned processes)
- [ ] Crash recovery cleans up orphaned Ollama

## Distribution

### macOS
- [ ] `python scripts/distribute_macos.py --dmg` creates DMG
- [ ] DMG mounts and shows app
- [ ] App runs from Applications folder

### Windows
- [ ] `python scripts/distribute_windows.py` creates installer
- [ ] Installer runs and installs app
- [ ] App runs from Start Menu
- [ ] Uninstaller works

## Documentation

- [ ] README.md is up to date
- [ ] DEVELOPMENT.md explains workflow
- [ ] DISTRIBUTION.md explains release process
- [ ] All phases documented in temp/phase*_updated.md

## Performance

- [ ] Application starts in reasonable time (< 30s)
- [ ] Chat responses begin streaming quickly
- [ ] No memory leaks during extended use
- [ ] Clean shutdown (no zombie processes)

## Security

- [ ] No hardcoded API keys in source
- [ ] User data stored in appropriate location
- [ ] Ollama bound to localhost only
- [ ] No sensitive data in logs

## Accessibility

- [ ] Keyboard navigation works
- [ ] Screen reader compatible
- [ ] High contrast mode supported
- [ ] Font sizes adjustable

---

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| Developer | | | |
| QA | | | |
| Release Manager | | | |
