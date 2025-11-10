# Contributing to Text2Mem

Thank you for your interest in contributing to Text2Mem! This document provides guidelines for contributing to the project.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Code Style](#code-style)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)

## 🤝 Code of Conduct

This project follows a standard Code of Conduct. Be respectful and constructive in all interactions.

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/Text2Mem.git`
3. Create a branch: `git checkout -b feature/your-feature-name`

## 💻 Development Setup

### Prerequisites

- Python 3.8+
- pip or conda

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/Text2Mem.git
cd Text2Mem

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Or using conda
conda env create -f environment.yml
conda activate text2mem
```

## 🎯 How to Contribute

### Reporting Bugs

- Use the GitHub issue tracker
- Describe the bug clearly
- Include steps to reproduce
- Provide system information (OS, Python version, etc.)

### Suggesting Enhancements

- Open an issue with the "enhancement" label
- Describe the feature and its use case
- Explain why this enhancement would be useful

### Code Contributions

1. **Pick an issue** or create one to discuss your changes
2. **Create a branch** from `main`
3. **Make your changes** following the code style
4. **Add tests** for new features
5. **Update documentation** if needed
6. **Submit a pull request**

## 📝 Code Style

### Python Code

We follow PEP 8 with some modifications:

```bash
# Format code with black
black text2mem/ tests/

# Sort imports with isort
isort text2mem/ tests/

# Type checking with mypy
mypy text2mem/
```

### Documentation

- Add docstrings to all public functions and classes
- Use Google-style docstrings
- Include type hints

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=text2mem tests/

# Run specific test file
pytest tests/test_engine.py
```

## 🔄 Pull Request Process

1. **Update documentation** if you've added new features
2. **Ensure all tests pass**: `pytest`
3. **Update CHANGELOG.md** with your changes
4. **Keep commits atomic and well-described**
5. **Reference related issues** in your PR description

### Commit Message Format

```
<type>: <subject>

<body>

<footer>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Text2Mem!** 🎉
