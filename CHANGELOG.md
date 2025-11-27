# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2024-11-27

### Added

#### Compliance Guardrail Layer
A comprehensive final processing layer for financial outputs that ensures regulatory compliance:

- **Output Scanning**: Detects prescriptive verbs, advice patterns, opinions-as-fact, and certainty language
- **Advice Removal**: Context-aware pattern matching with regex capture groups for grammatical replacements
- **Prescriptive Verb Blocking**: Comprehensive patterns for "should", "must", "recommend", and more
- **Descriptive Tone Enforcement**: Converts advice to descriptive language with post-processing grammar cleanup
- **Automatic Disclaimers**: Region and asset-class appropriate disclaimers when missing

#### Multilingual Compliance Support (9 Languages)
- English (en) - Full support with comprehensive patterns
- Spanish (es) - Prescriptive verbs, advice patterns, disclaimers
- French (fr) - Prescriptive verbs, advice patterns, disclaimers
- German (de) - Prescriptive verbs, advice patterns, disclaimers
- Italian (it) - Prescriptive verbs, advice patterns, disclaimers
- Portuguese (pt) - Prescriptive verbs, advice patterns, disclaimers
- Japanese (ja) - Script detection, advice patterns, disclaimers
- Chinese (zh) - Script detection, advice patterns, disclaimers
- Farsi/Persian (fa) - Script detection, advice patterns, disclaimers

#### New Components
- `SupportedLanguage` enum for language specification
- `MultilingualPatterns` class with language-specific pattern dictionaries
- `GuardrailResult` dataclass with detected language field
- `ComplianceGuardrail` class with configurable thresholds
- `_cleanup_grammar()` method for post-replacement grammar fixes

#### NarrativeValidator Integration
- `process_with_guardrail()` method for seamless integration with existing narrative validation

### Changed
- Improved pattern matching for better grammatical correctness in replacements
- Added configurable thresholds (`LANGUAGE_DETECTION_MIN_SCORE`, `STRICT_MODE_MAX_VIOLATIONS`)
- Enhanced automatic language detection (script-based for CJK/Arabic, word-based for Latin scripts)

### Technical Details
- 91 guardrail-specific tests
- 163 total compliance-related tests passing
- Zero CodeQL security alerts
- Full backward compatibility with existing compliance components

## [0.2.2] - Previous Release

See previous release notes for changes prior to 0.3.0.
