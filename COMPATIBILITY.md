# Platform Compatibility

This document outlines the platform compatibility of `incode-cli` installation scripts.

## ✅ Supported Platforms

| Platform | Status | Tested | Notes |
|----------|--------|--------|-------|
| **macOS** | ✅ Supported | Yes | macOS 10.15+ (Catalina and newer) |
| **Linux** | ✅ Supported | Yes | Most distributions (Ubuntu, Debian, Fedora, Arch, etc.) |
| **Windows** | ❌ Not Supported | No | Use WSL2 (Windows Subsystem for Linux) |

## 🔧 Requirements

### All Platforms
- **Bash**: Version 4.0+ (macOS includes bash 3.2, but scripts are compatible)
- **Python**: Version 3.9 or higher
- **Git**: For cloning the repository
- **curl**: For one-liner installation (usually pre-installed)

### Shell Configuration
The scripts create a symlink in `~/.local/bin/incode`. Make sure this directory is in your `PATH`:

**Bash** (`~/.bashrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Zsh** (`~/.zshrc`):
```bash
export PATH="$HOME/.local/bin:$PATH"
```

**Fish** (`~/.config/fish/config.fish`):
```fish
set -gx PATH $HOME/.local/bin $PATH
```

After adding, reload your shell:
```bash
source ~/.bashrc  # or ~/.zshrc, or restart terminal
```

## 🖥️ macOS-Specific

### Python Installation
macOS doesn't include Python 3 by default. Install via:

**Homebrew** (recommended):
```bash
brew install python@3.11
```

**Official Installer**:
Download from [python.org](https://www.python.org/downloads/macos/)

### Compatibility Notes
- ✅ ANSI color codes work in Terminal.app and iTerm2
- ✅ Version comparison works without GNU `sort`
- ✅ All bash built-ins are compatible with macOS bash 3.2+

## 🐧 Linux-Specific

### Python Installation

**Debian/Ubuntu**:
```bash
sudo apt update
sudo apt install python3 python3-venv python3-pip
```

**Fedora**:
```bash
sudo dnf install python3 python3-pip
```

**Arch Linux**:
```bash
sudo pacman -S python python-pip
```

### Compatibility Notes
- ✅ Works on all major distributions
- ✅ Works with both Bash and Zsh
- ✅ Compatible with systemd and non-systemd systems

## 🪟 Windows (via WSL2)

Windows users should use **WSL2** (Windows Subsystem for Linux):

1. **Enable WSL2**:
   ```powershell
   wsl --install
   ```

2. **Install Ubuntu** (or another distro):
   ```powershell
   wsl --install -d Ubuntu
   ```

3. **Follow Linux installation** inside WSL2

## 🧪 Cross-Platform Script Features

### What Works Everywhere

| Feature | Implementation | Compatibility |
|---------|---------------|---------------|
| Color output | ANSI escape codes | ✅ macOS, Linux |
| Version comparison | Pure bash implementation | ✅ macOS (bash 3.2+), Linux |
| Virtual environment | Python `venv` module | ✅ Python 3.3+ (all platforms) |
| Symlink creation | `ln -s` | ✅ macOS, Linux, WSL2 |
| Path detection | `$HOME/.local/bin` | ✅ XDG standard (all platforms) |

### Cross-Platform Testing

The scripts use **portable bash** and avoid:
- ❌ GNU-specific flags (e.g., `sort -V`)
- ❌ Linux-only commands (e.g., `lsb_release`)
- ❌ macOS-only commands (e.g., `sw_vers`)
- ❌ Bashisms that don't work in older bash versions

## 🔍 Troubleshooting

### "Python 3 not found"
**Solution**: Install Python 3.9+ using your package manager

### "~/.local/bin not in PATH"
**Solution**: Add `export PATH="$HOME/.local/bin:$PATH"` to your shell config

### "Permission denied" when running scripts
**Solution**: Make scripts executable:
```bash
chmod +x install.sh uninstall.sh quick-install.sh
```

### "Command not found: incode"
**Solution**: 
1. Check symlink: `ls -la ~/.local/bin/incode`
2. Verify PATH: `echo $PATH | grep '.local/bin'`
3. Restart terminal or run: `source ~/.bashrc` (or `~/.zshrc`)

## 📝 Testing Checklist

Before releasing updates, test on:

- [ ] macOS 13+ (Ventura)
- [ ] macOS 12 (Monterey)
- [ ] Ubuntu 22.04 LTS
- [ ] Ubuntu 20.04 LTS
- [ ] Debian 11
- [ ] Fedora (latest)
- [ ] Arch Linux
- [ ] WSL2 (Ubuntu)

---

**Last Updated**: 2026-01-25
