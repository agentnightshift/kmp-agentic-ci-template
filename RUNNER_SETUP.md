# Self-Hosted GitHub Actions Runner Setup (macOS)

This guide explains how to set up your local Mac as a self-hosted GitHub Actions runner for the `ui_verification` job.

## Prerequisites

- macOS 12 (Monterey) or later
- Admin access to the GitHub repository
- Android SDK installed with emulator configured
- Java 17 installed

---

## Step 1: Download the Runner

Navigate to your repository on GitHub:

```
Settings → Actions → Runners → New self-hosted runner
```

Select **macOS** and follow the commands, or use these:

```bash
# Create a directory for the runner
mkdir -p ~/actions-runner && cd ~/actions-runner

# Download the latest runner (check GitHub for current version)
curl -o actions-runner-osx-arm64-2.321.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-osx-arm64-2.321.0.tar.gz

# Extract the installer
tar xzf ./actions-runner-osx-arm64-2.321.0.tar.gz
```

> **Note**: For Intel Macs, use `actions-runner-osx-x64-*.tar.gz` instead.

---

## Step 2: Configure the Runner

Get a registration token from GitHub:

```
Settings → Actions → Runners → New self-hosted runner → Copy the token
```

Run the configuration:

```bash
cd ~/actions-runner

# Configure the runner (replace placeholders)
./config.sh --url https://github.com/OWNER/REPO --token YOUR_TOKEN

# When prompted:
#   - Runner group: [Enter for default]
#   - Runner name: my-mac-runner (or any name)
#   - Labels: self-hosted,macOS,ARM64 (default is fine)
#   - Work folder: [Enter for default]
```

---

## Step 3: Run as a Service

### Option A: LaunchDaemon (Recommended for CI)

This keeps the runner alive across reboots and user logouts:

```bash
cd ~/actions-runner

# Install the service
sudo ./svc.sh install

# Start the service
sudo ./svc.sh start

# Check status
sudo ./svc.sh status
```

**Service management commands:**

```bash
sudo ./svc.sh stop      # Stop the runner
sudo ./svc.sh uninstall # Remove the service
```

### Option B: Run Manually (For Testing)

```bash
cd ~/actions-runner
./run.sh
```

---

## Step 4: Verify the Runner

1. Go to your repository on GitHub
2. Navigate to `Settings → Actions → Runners`
3. Confirm your runner appears with a **green** "Idle" status

---

## Emulator Setup

Ensure the Android emulator is running before PRs trigger the workflow:

```bash
# List available emulators
emulator -list-avds

# Start an emulator (headless for CI)
emulator -avd Pixel_6_API_34 -no-window -no-audio -no-boot-anim &

# Wait for boot completion
adb wait-for-device shell 'while [[ -z $(getprop sys.boot_completed) ]]; do sleep 1; done'
```

### Auto-Start Emulator on Login

Create a LaunchAgent to start the emulator automatically:

```bash
cat > ~/Library/LaunchAgents/com.android.emulator.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.android.emulator</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/YOUR_USERNAME/Library/Android/sdk/emulator/emulator</string>
        <string>-avd</string>
        <string>Pixel_6_API_34</string>
        <string>-no-window</string>
        <string>-no-audio</string>
        <string>-no-boot-anim</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF

# Load the agent
launchctl load ~/Library/LaunchAgents/com.android.emulator.plist
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Runner offline | Check `sudo ./svc.sh status` and restart if needed |
| Emulator not found | Ensure `ANDROID_HOME` is set in runner environment |
| Permission denied | Verify runner has access to project directories |
| Tests timeout | Increase emulator resources or test timeouts |

### View Runner Logs

```bash
# Service logs
tail -f ~/actions-runner/_diag/Runner_*.log

# Worker logs
tail -f ~/actions-runner/_diag/Worker_*.log
```
