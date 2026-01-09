# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Initial added changelog and version file.

### Fixed
- N/A

### Changed
- N/A

## [0.1.1] - 2026-01-09
### Added 
- Manually triggered Event Lambdas for all Event Lambdas.
- Cleanup Uploads Event Lambda, deletes files with "uploading" status from database.
- Eventbridge schedule to run Cleanup Uploads Event Lambda.
- Endpoint to trigger manual file transfers.

### Changed
- Update Eventbridge Lambda Scheduler role to be extendable to other Lambdas.

## [0.0.0] - 2025-11-05
### Added
- Historical commits prior to this version are not individually listed.