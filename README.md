<div align="center">

![incode-cli Banner](.github/banner.png)

[![Version](https://img.shields.io/badge/version-2.16.5-blue.svg?style=flat-square)](https://github.com/manueloberberger/incode-cli) ![Python](https://img.shields.io/badge/python-3.9%2B-green?style=flat-square) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](LICENSE)

**The lightning-fast, keyboard-driven interface for the Red Cross duty roster.**

[Installation](#-installation) • [Features](#-features) • [Usage](#-usage) • [Contributing](#-contributing)

</div>

---

## ✨ Features

- 🚀 **Lightning Fast**: Optimized startup and navigation
- ⌨️ **Keyboard-Driven**: Efficient TUI (Terminal User Interface)
- 👥 **Multi-User Support**: Manage multiple accounts
- 📊 **Duty Roster Management**: View and manage your shifts
- 📇 **Staff Directory**: Quick access to contact information
- 📈 **Statistics & Analytics**: Track your work hours
- 🔄 **Smart Auto-Updates**: Self-updating app & background services
- 🔒 **Secure & Local**: Credentials stored locally on your machine

---

## 🚀 Installation

### Quick Install (One-Liner)

```bash
curl -sSL https://raw.githubusercontent.com/manueloberberger/incode-cli/main/quick-install.sh | bash
```

This automatically clones the repository to `~/.local/share/incode-cli` and installs everything.

### Manual Install

```bash
# 1. Clone the repository
git clone https://github.com/manueloberberger/incode-cli.git
cd incode-cli

# 2. Run the installer
./install.sh
```

The installer will:
- ✅ Check Python version (3.9+ required)
- ✅ Create a virtual environment
- ✅ Install dependencies
- ✅ Create a global `incode` command in `~/.local/bin`

> **Note**: Make sure `~/.local/bin` is in your PATH. Add this to your `~/.zshrc` or `~/.bashrc`:
> ```bash
> export PATH="$HOME/.local/bin:$PATH"
> ```

### Uninstall

```bash
./uninstall.sh
```

This removes the symlink, virtual environment, and optionally your credentials.

---

## 💡 Usage

Run from anywhere:

```bash
incode
```

Or use the local wrapper:

```bash
./incode
```

*On the first run, you will be prompted for your Incode credentials. They are stored securely and locally on your machine.*

---

## 🧪 Testing

To verify cross-platform compatibility on your system:

```bash
./test-compatibility.sh
```

This script checks:
- Bash syntax of installation scripts
- Required commands (python3, git, curl, etc.)
- Platform detection
- Python version
- PATH configuration

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for Red Cross volunteers**

</div>

