# WomCast Project Constitution

## Core Principles

### 1. Code Quality Standards
- **Type Safety**: All TypeScript code must use strict typing; Python code must pass `mypy --strict` with no `Any` types except where absolutely necessary
- **Linting**: Zero tolerance for lint errors; warnings must be addressed before merge
- **Code Review**: All changes require review focusing on readability, maintainability, and adherence to project patterns
- **Documentation**: Public APIs must have comprehensive docstrings; complex logic requires inline comments explaining "why" not "what"
- **DRY Principle**: Avoid duplication; extract shared logic into reusable functions/modules
- **Single Responsibility**: Each module, class, or function should have one clear purpose

### 2. Testing Standards
- **Coverage Minimums**: Unit test coverage ≥ 80% for critical paths; 100% for public APIs
- **Test Pyramid**: Prioritize unit tests > integration tests > e2e tests
- **Test Quality**: Tests must be readable, maintainable, and test behavior not implementation
- **Fast Feedback**: Unit tests must run in < 5 seconds; full suite < 2 minutes
- **CI Gates**: All tests must pass before merge; no flaky tests tolerated
- **Performance Tests**: Critical paths (USB indexing, AI queries, casting setup) must have performance regression tests

### 3. User Experience Consistency
- **10-Foot UI Design**: All interfaces optimized for TV viewing distance (3+ meters)
- **Navigation**: D-pad/remote-first navigation; keyboard/mouse as secondary inputs
- **Response Time**: UI interactions must respond within 100ms; feedback for operations > 500ms
- **Accessibility**: High contrast modes; large touch targets (≥ 48px); screen reader support where applicable
- **Error Handling**: User-friendly error messages with clear next steps; no technical jargon in UI
- **Consistency**: Uniform design language across all screens; predictable interaction patterns

### 4. Performance Requirements
- **Boot Time**: System ready for interaction within 45 seconds of power-on
- **USB Indexing**: 1000 media files indexed and searchable within 5 seconds
- **AI Query Response**: Intent recognition and response within 3 seconds
- **Casting Setup**: Device discovery and connection establishment within 2 seconds
- **Video Playback**: Start playback within 2 seconds; seek operations < 1 second
- **Memory Footprint**: Core system < 2GB RAM usage; leave headroom for media playback
- **Frame Rate**: UI animations maintain 60 fps; no jank on navigation

### 5. Security & Privacy
- **Local-First**: All processing happens on-device unless explicitly connecting to user-chosen cloud services
- **Data Minimization**: Collect only data necessary for functionality; no telemetry without opt-in
- **Secure Defaults**: Services bound to localhost; network exposure requires explicit configuration
- **Dependency Auditing**: Regular security scans (pip-audit, npm audit); no high/critical vulnerabilities in production
- **Token Management**: Secure storage of API keys and tokens; rotation mechanisms in place
- **Update Security**: Signed OTA updates; rollback capability on failed updates

### 6. Reliability & Stability
- **Graceful Degradation**: System remains functional when optional services fail (e.g., AI, casting)
- **Error Recovery**: Automatic retry with exponential backoff for transient failures
- **Logging**: Structured logging with appropriate levels; errors include context for debugging
- **Monitoring**: Key metrics (playback health, service status) logged for troubleshooting
- **Resource Management**: Proper cleanup of file handles, network connections, and memory
- **Crash Handling**: Automatic service restart; preserve user state where possible

### 7. Open Source & Community
- **License Compliance**: All dependencies must be compatible with project license; maintain SBOM
- **No DRM**: Exclude DRM and proprietary extraction modules; focus on open/free content
- **Contribution Guidelines**: Clear documentation for setup, development workflow, and PR standards
- **Reproducible Builds**: Documented build process; deterministic outputs where possible
- **Attribution**: Proper credit for third-party code, assets, and content sources

### 8. Development Workflow
- **Small Commits**: Atomic commits with clear messages following conventional commit format
- **Branch Strategy**: Feature branches from main; fast-forward merges preferred
- **CI/CD Pipeline**: Automated build, test, lint, and security checks on every push
- **Quality Gates**: All gates must pass before merge; no "fix it later" exceptions
- **Documentation Updates**: CHANGELOG.md, ASBUILT.md, and RUNBOOK.md updated with each significant change
- **Task Tracking**: Use task timing scripts; maintain UTC timestamps for all task events

## Decision Framework

When making architectural or implementation decisions, prioritize in this order:
1. **User Experience**: Does this improve usability and delight?
2. **Performance**: Does this meet our performance budgets?
3. **Maintainability**: Will this be easy to understand and modify in 6 months?
4. **Security/Privacy**: Does this protect user data and system integrity?
5. **Simplicity**: Is this the simplest solution that meets requirements?

## Enforcement

- Constitution violations flagged in code review
- CI pipeline enforces measurable standards (lint, test coverage, performance budgets)
- Regular retrospectives to refine principles based on team experience
- Constitution updates require team consensus and documentation of rationale
