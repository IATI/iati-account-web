# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.4.2 - 2025-12-08

### Added

- Custom exception handler to simplify error detection/handling throughout the application and drive users to the correct error pages.
- Register Your Data support code that simplifies calls made to the RYD API which again simplifies the view function code and makes the application more testable and robust.
- Organisation deletetion functionality.
- Organisation user management.

### Changes

- Refactors organisation editing, creation, joining and listing.
- Fixes a bug where the name of one of the message notification CSS classes was incorrect.


## 0.4.1 - 2025-12-03

### Added

- Preflight checks: `okay_to_continue` alongside `not_okay_to_continue` to allow us to start migrating away from the latter before the codebase becomes more extensive.
- User account: added `use_cases_using_data` field and changed forms/interfaces to reflect this change.
- Additional view at `/identity/post-login` to log successful logins.

### Changed

- Use django message framework to pass messages (success, errors, etc.) between views.
- Updated copy on the public landing, onboarding, and self-service pages in response to feedback.
- Large factoring of identity code, error handling and logging:
    - Moves most code that writes changes to the identity service into the User model where the actual fields are located so that changes in the User model and claims in the user model can be more easily kept in sync.  The remaining code is changed to an `oidc.py` module with the exception of the two view functions, that are moved into `views.py` in the root of the Django project.
    - Exception handling and logging is more thoroughly incorporated in all the identity service code.  A basic (non-encrypted) audit log is added to start capturing data before we go live.
    - Account provisioninng code is refactored to improve error handling, error reporting, and logging.
- Small fix to remove the preflight check from the welcome view, otherwise the use would never see the public landing page.
- Small UI change to the main navigation to hide it from view when not logged in.
