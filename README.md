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

This application currently is a skeleton that will form the basis of IATI Account Web.  At the moment the application supports single sign on to Asgardeo and displaying the resulting
user model and claims that have been obtained from the identity service.

Running this application locally and opening `https://localhost:8000` allows the user to login to Asgardeo using one of our development accounts.

## Development

### Running locally

Running this application locally and logging in to Asgardeo should not be done under HTTP as client secrets and user details will be passed via easily intercepted communications.  Local development should be done using SSL/TLS.

The development dependencies include `django_extensions` and `werkzeug` that together with using `runserver_plus` can launch a local server with SSL.  To do this, we first need to generate a certificate and private key.

This can be done using `openssl`:

```
openssl req -x509 -newkey rsa:4096 -keyout private-key.pem -out certificate.pem -sha256 -days 365 -nodes -subj "/C=GB/O=Open Data Services Co-operative Ltd./CN=api.eu.asgar
deo.io"
```

The Django can be run over HTTPS using

```
python manage.py runserver_plus --cert-file certificate.pem --key-file private-key.pem
```

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

