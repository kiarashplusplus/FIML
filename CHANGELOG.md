# Changelog

All notable changes to FIML (Financial Intelligence Meta-Layer) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- SECURITY.md with comprehensive security policy and best practices
- GitHub issue templates for bug reports and feature requests
- Pull request template with comprehensive checklist
- .editorconfig for consistent code formatting across editors

### Changed
- Updated GitHub Actions to latest versions (checkout@v4, setup-python@v5, cache@v4)
- Improved CI/CD configuration with better error handling

### Fixed
- 258 linting issues (removed whitespace, unused imports, fixed f-strings)
- Added per-file ignores for intentional FastAPI patterns

## [0.2.1] - 2025-11-23

### Added
- Agent workflows for deep equity analysis and crypto sentiment
- Azure OpenAI integration for narrative generation (500+ lines)
- Watchdog system for real-time market monitoring
- Session management with Redis + PostgreSQL dual storage
- Performance testing suite with benchmarks and load tests
- Cache warming and intelligent eviction policies

### Changed
- Improved cache architecture with L1/L2 optimization
- Enhanced multi-agent orchestration with Ray framework

### Fixed
- 238 deprecation warnings (datetime.utcnow usage)
- SQLAlchemy metadata handling
- Cache optimization for batch operations

## [0.2.0] - 2025-11-15

### Added
- Multi-agent orchestration framework (7 specialized agents)
- Real-time WebSocket streaming (650 lines)
- Compliance framework for 8 regions
- Dashboard with alerts and monitoring

### Changed
- Enhanced arbitration engine with 5-factor scoring
- Improved provider system with CCXT integration

## [0.1.1] - 2025-11-10

### Fixed
- Test infrastructure improvements
- CI/CD pipeline enhancements

## [0.1.0] - 2025-11-01

### Added
- Initial release
- Core MCP server implementation (450 lines)
- Data arbitration engine (350 lines)
- Provider abstraction layer (1,900 lines)
- Yahoo Finance, Alpha Vantage, FMP, CCXT, Mock providers
- L1/L2 cache architecture (530 lines)
- FK-DSL parser and execution framework (550 lines)
- Docker and Kubernetes deployment
- CI/CD pipeline with GitHub Actions
- Comprehensive test framework (439 tests)

[Unreleased]: https://github.com/kiarashplusplus/FIML/compare/v0.2.1...HEAD
[0.2.1]: https://github.com/kiarashplusplus/FIML/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/kiarashplusplus/FIML/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/kiarashplusplus/FIML/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/kiarashplusplus/FIML/releases/tag/v0.1.0
