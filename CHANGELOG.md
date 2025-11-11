# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-10

### Added
- Step 6 AI-native narrative v0.2 (deterministic templates, zh-Hant/en, AI_NATIVE toggle)
- Step 5 coach tips engine + export pack
- Step 4 events/cards + summary endpoint
- Acceptance scripts up to step6, new step7 demo kit

### Changed
- Updated narrative API to return list of lines instead of dictionary format
- Enhanced build_narrative function with multilingual support (zh-Hant/en)
- Added deterministic template selection using hash-based indexing
- Improved fallback behavior when AI_NATIVE is disabled

### Fixed
- Fixed narrative response format consistency across endpoints
- Updated tests to work with new narrative API format
- Resolved issues with AI_NATIVE toggle functionality

## [0.1.2] - Previous Release

### Added
- Basic telemetry import functionality
- Event detection system
- Simple summary endpoints

### Changed
- Initial API structure