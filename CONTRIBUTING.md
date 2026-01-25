# Contributing to incode-cli 🚑

Thank you for considering contributing to **incode-cli**! This document outlines the process for contributing to the project.

---

## 🚀 Getting Started

### 1. Fork & Clone

```bash
# Fork the repository on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/incode-cli.git
cd incode-cli
```

### 2. Install Development Environment

```bash
# Run the installer
./install.sh

# Install development dependencies (if any)
pip install pytest mypy
```

### 3. Create a Branch

```bash
git checkout -b feature/your-feature-name
```

---

## 🛠️ Development Workflow

### Running the Application

```bash
# Using the wrapper script
./incode

# Or directly with Python
.venv/bin/python3 incode.py
```

### Code Quality

We use `mypy` for type checking. Before committing:

```bash
# Type check
.venv/bin/python3 -m mypy incode.py src/

# Run tests
.venv/bin/python3 -m pytest
```

### Code Style

- Follow PEP 8 conventions
- Use type hints where possible
- Add docstrings for new functions/classes
- Keep functions focused and well-named

---

## 📝 Commit Guidelines

Use clear, descriptive commit messages:

```bash
# Good examples:
git commit -m "Add support for filtering duties by date range"
git commit -m "Fix crash when no internet connection"
git commit -m "Refactor API client for better error handling"

# Bad examples:
git commit -m "fix"
git commit -m "update stuff"
```

---

## 🔄 Pull Request Process

1. **Update Documentation**: If you add new features, update the README
2. **Test Your Changes**: Ensure the app still works as expected
3. **Push to Your Fork**:
   ```bash
   git push origin feature/your-feature-name
   ```
4. **Create Pull Request**: Go to GitHub and create a PR from your fork
5. **Describe Your Changes**: Explain what and why in the PR description

---

## 🐛 Reporting Bugs

Found a bug? Please create an issue with:

- **Description**: What happened vs what you expected
- **Steps to Reproduce**: How to trigger the bug
- **Environment**: OS, Python version, incode-cli version
- **Logs**: Any error messages or stack traces

---

## 💡 Feature Requests

Have an idea? Great! Please:

1. Check if it's already been suggested
2. Open an issue describing your feature
3. Explain the use case and benefits

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

**Thank you for making incode-cli better! 🙏**
