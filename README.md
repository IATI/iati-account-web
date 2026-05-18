# IATI Account (Web App)

## Summary

 Product  | IATI Account (Web App) 
--- | ---
Description | The IATI Account product is a web app for users to self-manage their accounts and to make write changes into the new IATI Registry. 
Website | None 
Related |
Documentation | Rest of README.md
Technical Issues | [GitHub issues page](https://github.com/IATI/iati-account-web/issues) 
Support | [IATI Support Website](https://iatistandard.org/en/guidance/get-support/) 

## High-level requirements

* Python 3.12.11

## Overview

This application is the main tool through which IATI users can self-service their accounts, create and delete reporting organisations, and manage dataset urls that are part of the IATI corpus.

Running this application locally and opening `https://localhost:8443` allows the user to login to Asgardeo using one of our development accounts.

## Development

### Running locally

Configuration is through environment variables.  The application will get environment variables from the local environment, or through a ".env" file that is specified through the environment variable ENV_FILE.

To run, the application needs a database. When running locally it will (create) and
use a new SQLite database automatically by default, but migrations need to be
run before starting the server:

```bash
ENV_FILE=.env.dev python manage.py migrate
```

Running this application locally and logging in to Asgardeo should not be done under HTTP as client secrets and user details will be passed via easily intercepted communications.  Local development should be done using SSL/TLS.

The development dependencies include `django_extensions` and `werkzeug` that together with using `runserver_plus` can launch a local server with SSL.  To do this, we first need to generate a certificate and private key.

This can be done using `openssl`:

```
openssl req -x509 -newkey rsa:4096 -keyout private-key.pem -out certificate.pem -sha256 -days 365 -nodes -subj "/C=GB/O=Open Data Services Co-operative Ltd./CN=api.eu.asgar
deo.io"
```

Now the Django app can be run over HTTPS using

```
python manage.py runserver_plus "127.0.0.1:8443" --cert-file certificate.pem --key-file private-key.pem
```

It will be accessible on: [https://localhost:8443](https://localhost:8443)

There is a bash script that automates this:
```
ENV_FILE=.env.dev ./runserver.sh
```


### Automated tests

There are some automated tests that run entirely in Django without the need for external dependencies or services (e.g., Mockoon).  The test environment variables must be used `.env.test.`:

```bash
ENV_FILE=.env.test python manage.py test
```

### Environment variables
| Variable                    | Description                                                  |
| --------------------------- | ------------------------------------------------------------ |
| `ALLOWED_HOSTS`             | Comma separated list of allowed hosts. |
| `APP_LOG_FILE`              | Path to the application log file. |
| `AUDIT_LOG_FILE`            | Path to the audit log file. |
| `AUDIT_LOG_PUBLIC_KEY_FILE` | Path to a public key file used to encrypt the audit log.  This can be empty, in which case the audit log will be unencrypted. |
| `APP_LOG_LEVEL`             | Logging level for the application log. |
| `AUDIT_LOG_LEVEL`           | Logging level for the audit log. |
| `DJANGO_LOG_LEVEL`          | Logging level for the Django log. |
| `OIDC_LOG_LEVEL`            | Logging level for the OIDC plugin log. |
| `REQUESTS_LOG_LEVEL`        | Logging level for the request library log. |
| `CRM_BASE_URL`              | Base URL for the CRM. |
| `CRM_CLIENT_ID`             | Client ID for the CRM connection. |
| `CRM_CLIENT_SECRET`         | Client secret for the CRM connection. |
| `DEBUG`                     | Debug setting for Django. |
| `ENV_FILE`                  | Path to a .env file to load. |
| `IDENTITY_SERVICE_BASE_URL` | Base URL for the identity service (used to backend account communication). |
| `IDENTITY_SERVICE_CLIENT_ID` | Client ID for the identity service connection. |
| `IDENTITY_SERVICE_CLIENT_SECRET` | Client secret for the identity service connection. |
| `IDENTITY_SERVICE_ROLE_ID_IATI_REGISTER_YOUR_DATA` | UUID for the `iati_register_your_data` role in the identity service. |
| `OIDC_OP_AUTHORIZATION_ENDPOINT` | Identity service authorisation endpoint URL. |
| `OIDC_OP_JWKS_ENDPOINT`     | Identity service JWKS endpoint URL. |
| `OIDC_OP_TOKEN_ENDPOINT`    | Identity service token endpoint URL. |
| `OIDC_OP_USER_ENDPOINT`     | Identity service user info endpoint URL. |
| `OIDC_RENEW_ID_TOKEN_EXPIRY_SECONDS` | Duration after which the ID token expires and needs to be obtained again by logging into the identity server. |
| `OIDC_RP_CLIENT_ID`         | Client ID for the identity service (used for end user OIDC login). |
| `OIDC_RP_CLIENT_SECRET`     | Client secret for the identity service (used for end user OIDC login). |
| `POSTGRES_NAME`             | Name for the PSQL database. |
| `POSTGRES_USER`             | User for the PSQL database. |
| `POSTGRES_PASSWORD`         | Password for the PSQL database. |
| `POSTGRES_HOST`             | Host for the PSQL database. |
| `POSTGRES_PORT`             | Port for the PSQL database. |
| `REGISTER_YOUR_DATA_ALLOW_REDIRECTS` | Whether to allow redirects when communicating with Register Your Data. |
| `REGISTER_YOUR_DATA_BASE_URL` | Base URL for the Register Your Data API. |
| `REGISTER_YOUR_DATA_DISCOVERABLE_REPORTING_ORGS_PAGE_SIZE` | Page size when fetching discoverable reporting orgs. |
| `REGISTER_YOUR_DATA_STRIP_AUTH_CHECK` | Strip authorisation information during redirects when communicating with Register Your Data. |
| `SECRET_KEY`                | Django secret key. |
| `SERVE_PROM_APP_METRICS`    | Flag to start serving prometheus metrics. |
| `SERVER_URL_BASE`           | Base URL for the application. |
| `STATIC_ROOT`               | Location for static files. |

### Adding new dependencies

New dependencies are added to `pyproject.toml`.  Once these have been added `requirements.txt` and/or `requirements_dev.txt` need to be regenerated.  With:

```
pip-compile --output-file=requirements.txt --strip-extras
```

and/or

```
pip-compile --extra=dev --output-file=requirements_dev.txt --strip-extras
```

### Checking and linting

Linting is setup with `isort` and `black` and checked with `flake8`.  Static type checking is performed by `mypy`.  Configurations are stored in `pyproject.toml`.  To use these linters and checkers you will first need to install the development dependencies:

```
pip install -r requirements_dev.txt
```

Then the code can be linted with:

```
black .
isort .
```

And checked with flake8 and mypy:

```
flake8
mypy .
```

### Security testing
Static Security Application Testing is performed with `bandit`.  To use this tool you must also install the development dependencies and then test with:

```
bandit -c pyproject.toml -r .
```

### Versioning

The version is set in `pyproject.toml`.  When making updates, set the version to an appropriate value.


## License
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    
    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.
    
    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

