# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## 0.4.13 - 2026-04-15

### Fixed

- Fixed editor permissions to allow updating dataset visibility.

## 0.4.12 - 2026-03-16

### Fixed

- Fixed broken country filtering when users try to join a reporting organisation.

### Added

- Added timezones to logs.
- Basic superadmin view, allowing users to search for a reporting organisation and navigate to that organisation.
- Improved testing framework for verifying authenticated and controlled access to the superadmin view.
- Tests now run in CI.

### Changes

- Lengthened timeout duration for login sessions.
- Improved handling of permission denied exceptions.

## 0.4.11 - 2026-02-23

### Fixed

- Fixed bug preventing updates to dataset visibility status
- A few other small fixes to the dataset edit form

## 0.4.10 - 2026-02-18

### Fixed

- Made Delete Organisation button visible for super admins

## 0.4.9 - 2025-12-19

### Added

- Detects superadmins on login and shows a navigation menu item for future superadmin pages.

### Changes

- Adds super_admin role to the UserAndRole model and updates user role text at the top of pages.

## 0.4.8 - 2025-12-19

### Added

- Link to help site.
- Basic CLI audit log viewer to support debugging.

### Changes

- Remove Django admin pages.
- Fixed error where users could not select the dataset page size.
- Removed mailing list subscriptions from account completion.
- Fixed bug where join organisation page could cause a crash from an empty form submission.

## 0.4.7 - 2025-12-16

### Added

- Environment variable to control whether or not prometheus metrics are served.

### Changes

- Allow passing "None" as an audit log public key filename to suppress encrypted logging.

## 0.4.6 - 2025-12-16

### Added

- Complete registration page that users will be redirected to after self-registering via third party applications.
- Add user registry id to audit log entries to aid debugging.

### Changes

- Default dataset visibility is now public.
- Reword "Publisher Data Portal" to "Data Portal" and add some basic validation.
- Hide user role dropdowns when users do not have permissions to change user roles.
- Fix empty links to create reporting organisation page.
- Fix "view datasets" button on reporting organisation page.

## 0.4.5 - 2025-12-15

### Added

- Form styling to indicate required fields.
- Some additional form field validation.
- User home page.
- Load all discoverable reporting organisations.
- Page breadcrumbs to aid navigation.

### Changes

- Fixes issues on organisation page with missing fax number and RYD payload.
- Clean up page footer.
- Force user account provisioning check after every login.
- Layout changes in reporting organisation page.

## 0.4.4 - 2025-12-11

### Added

- Encrypted audit logging.
- Enhanced application logging to named files.

### Changes

- Bug fixes to provisioning code.

## 0.4.3 - 2025-12-09

### Added

- Dataset list, dataset editing, dataset deletion, and dataset creation.
- Dataset model, RYD handling code and pagination parser so that pagination options can be presented to the user.

### Changes

- Added code to write the stack trace into logs from the custom exception middleware.
- Customised log formatting to provide more detail and aid debugging.

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
