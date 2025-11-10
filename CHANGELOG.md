# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Complete benchmark system with generation, validation, and testing workflows
- Unified CLI tool (`bench-cli`) for all benchmark operations
- Comprehensive documentation (README, GUIDE, TEST_REPORT)
- MIT License
- Contributing guidelines
- This changelog

### Changed
- Refactored benchmark data structure for clarity
- Improved .gitignore to exclude generated data and artifacts
- Cleaned up redundant files and directories

## [0.2.0] - 2024-10-XX

### Added
- Provider vs Service separation for better model abstraction
- Mock, Ollama, and OpenAI provider support
- Service factory pattern for model services
- Thirteen memory operations: Encode, Retrieve, Summarize, Label, Update, Merge, Split, Promote, Demote, Lock, Expire, Delete, Clarify (reserved)

### Changed
- Upgraded to Pydantic v2
- Improved validation with JSON Schema + Pydantic dual validation
- Enhanced CLI with multiple operation modes

### Fixed
- Various bug fixes and stability improvements

## [0.1.0] - 2024-09-XX

### Added
- Initial release
- Core IR (Intermediate Representation) abstraction
- SQLite adapter for storage
- Basic CLI tooling
- Memory operation semantics
- Validation framework
- Test suite
- Examples and documentation

---

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Security fixes

[Unreleased]: https://github.com/your-repo/Text2Mem/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/your-repo/Text2Mem/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/your-repo/Text2Mem/releases/tag/v0.1.0
