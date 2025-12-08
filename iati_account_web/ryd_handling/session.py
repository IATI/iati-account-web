import logging
from json import JSONDecodeError
from urllib.parse import urljoin, urlparse

from iati_account_web.exceptions import (
    RegisterYourData404,
    RegisterYourDataBadRequest,
    RegisterYourDataPermissionDenied,
    RegisterYourDataResponseParsingIssue,
    RegisterYourDataServerIssue,
)
from iati_account_web.settings import env
from requests import HTTPError, Response, Session, Timeout

app_logger = logging.getLogger("iati_account")


class RegisterYourDataSession(Session):
    """Session subclass to provide automated error handling and URL construction when accessing RYD"""

    def __init__(self, access_token: str, allow_redirects=False):
        """Initialiser

        Parameters
        ----------
        access_token : str
            Access token to add as Bearer token to Authorization header.
        allow_redirects : bool, optional
            Allow redirects, by default False.
        """
        super().__init__()
        self.headers["Authorization"] = f"Bearer {access_token}"
        self.should_strip_auth = lambda old_url, new_url: False
        self._base_url = env("REGISTER_YOUR_DATA_BASE_URL").rstrip("/") + "/"
        self._allow_redirects = allow_redirects

    @staticmethod
    def _strip_auth_check(old_url: str, new_url: str) -> bool:
        """Check if authorisation data should be stripped on redirection.

        Parameters
        ----------
        old_url : str
        new_url : str

        Returns
        -------
        bool
            True means that authorisation data should be stripped.
        """
        old_url_parsed = urlparse(old_url)
        new_url_parsed = urlparse(new_url)
        if (old_url_parsed.hostname == new_url_parsed.hostname) and (old_url_parsed.path == new_url_parsed.path):
            return False
        return True

    def _build_url(self, url: str) -> str:
        """Build a URL for accessing the API.

        Parameters
        ----------
        url : str
            Path to add to the URL base obtained from Django settings.

        Returns
        -------
        str
        """
        return urljoin(self._base_url, url.lstrip("/"))

    def _handle_httperror(self, exc: HTTPError, ryd_data: dict) -> None:
        """Handle HTTPError exceptions, logging and raising custom exceptions.

        Parameters
        ----------
        exc : HTTPError
            HTTPError exception as raised by request().
        ryd_data : dict
            Dictionary of data from RYD.

        Raises
        ------
        RegisterYourDataPermissionDenied
        RegisterYourDataServerIssue
        RegisterYourDataBadRequest
        RegisterYourData404
        RegisterYourDataServerIssue
        """
        _request = f"{exc.response.request.method} {exc.response.url}"
        _httperr = f"HTTP {exc.response.status_code}"
        _ryderr = ryd_data.get("error", "") if isinstance(ryd_data, dict) else ""

        # These are separated out (rather than using response.status_reason) so
        # we can customise the response and figure out what custom exception
        # to raise.
        if exc.response.status_code in (401, 403):
            _err_msg = f"Permission denied ({_httperr}) in {_request} where RYD reported {_ryderr}"
            app_logger.warning(_err_msg)
            raise RegisterYourDataPermissionDenied(_err_msg)
        elif exc.response.status_code == 500:
            _err_msg = f"Server error ({_httperr}) in {_request} where RYD reported {_ryderr}"
            app_logger.warning(_err_msg)
            raise RegisterYourDataServerIssue(_err_msg)
        elif exc.response.status_code == 400:
            _err_msg = f"Bad request ({_httperr}) in {_request} where RYD reported {_ryderr}"
            app_logger.warning(_err_msg)
            raise RegisterYourDataBadRequest(_err_msg)
        elif exc.response.status_code == 404:
            _err_msg = f"Not found ({_httperr}) in {_request} where RYD reported {_ryderr}"
            app_logger.warning(_err_msg)
            raise RegisterYourData404(_err_msg)
        else:
            _err_msg = f"Unexpected error ({_httperr}) in {_request} where RYD reported {ryd_data.get("error", "")}"
            app_logger.warning(_err_msg)
            raise RegisterYourDataServerIssue(_err_msg)

    def _handle_timeout(self, exc: Timeout):
        """Handle Timeout exceptions raised by request()

        Parameters
        ----------
        exc : Timeout

        Raises
        ------
        RegisterYourDataServerIssue
        """
        _request = f"{exc.response.request.method} {exc.response.url}"
        app_logger.warning(f"Timeout in {_request}")
        raise RegisterYourDataServerIssue(f"Timeout in {_request}.")

    def _handle_jsondecodeerror(self, exc: JSONDecodeError, response: Response):
        """Handle JSON Decoding error exceptions raised when decoding RYD responses.

        Parameters
        ----------
        exc : JSONDecodeError
        response : requests.Response
            Response object so the method and url can be logged.

        Raises
        ------
        RegisterYourDataResponseParsingIssue
        """
        _request = f"{response.request.method} {response.url}"
        _err_msg = f"JSON decode error when parsing response from {_request} with exception {exc}"
        app_logger.warning(_err_msg)
        raise RegisterYourDataResponseParsingIssue(_err_msg)

    def _handle_unexpected(self, exc: JSONDecodeError, response: Response):
        """Handle unexpected exceptions when processing RYD responses.

        Parameters
        ----------
        exc : JSONDecodeError
        response : requests.Response
            Response object so the method and url can be logged.

        Raises
        ------
        RegisterYourDataServerIssue
        """
        _request = f"{response.request.method} {response.url}"
        _err_msg = f"Unexpected error in {_request} with exception {exc}"
        app_logger.warning(_err_msg)
        raise RegisterYourDataServerIssue(_err_msg)

    def get(self, url: str, **kwargs) -> dict:
        """GET method

        Parameters
        ----------
        url : str

        Returns
        -------
        dict
        """
        url = self._build_url(url)
        data = {}
        try:
            response = super().get(url, **kwargs, allow_redirects=self._allow_redirects)
            data = response.json()
            response.raise_for_status()
        except HTTPError as exc:
            self._handle_httperror(exc, data)
        except Timeout as exc:
            self._handle_timeout(exc)
        except JSONDecodeError as exc:
            self._handle_jsondecodeerror(exc, response)
        except Exception as exc:
            self._handle_unexpected(exc, response)

        return data

    def post(self, url: str, **kwargs) -> dict:
        """POST method

        Parameters
        ----------
        url : str

        Returns
        -------
        dict
        """
        url = self._build_url(url)
        data = {}
        try:
            response = super().post(url, **kwargs, allow_redirects=self._allow_redirects)
            data = response.json()
            response.raise_for_status()
        except HTTPError as exc:
            self._handle_httperror(exc, data)
        except Timeout as exc:
            self._handle_timeout(exc)
        except JSONDecodeError as exc:
            self._handle_jsondecodeerror(exc, response)
        except Exception as exc:
            self._handle_unexpected(exc, response)

        return data

    def put(self, url: str, **kwargs) -> dict:
        """PUT method

        Parameters
        ----------
        url : str

        Returns
        -------
        dict
        """
        url = self._build_url(url)
        data = {}
        try:
            response = super().put(url, **kwargs, allow_redirects=self._allow_redirects)
            data = response.json()
            response.raise_for_status()
        except HTTPError as exc:
            self._handle_httperror(exc, data)
        except Timeout as exc:
            self._handle_timeout(exc)
        except JSONDecodeError as exc:
            self._handle_jsondecodeerror(exc, response)
        except Exception as exc:
            self._handle_unexpected(exc, response)

        return data

    def patch(self, url: str, **kwargs) -> dict:
        """PATCH method

        Parameters
        ----------
        url : str

        Returns
        -------
        dict
        """
        url = self._build_url(url)
        data = {}
        try:
            response = super().patch(url, **kwargs, allow_redirects=self._allow_redirects)
            data = response.json()
            response.raise_for_status()
        except HTTPError as exc:
            self._handle_httperror(exc, data)
        except Timeout as exc:
            self._handle_timeout(exc)
        except JSONDecodeError as exc:
            self._handle_jsondecodeerror(exc, response)
        except Exception as exc:
            self._handle_unexpected(exc, response)

        return data

    def delete(self, url: str, **kwargs) -> dict:
        """DELETE method

        Parameters
        ----------
        url : str

        Returns
        -------
        dict
        """
        url = self._build_url(url)
        data = {}
        try:
            response = super().delete(url, **kwargs, allow_redirects=self._allow_redirects)
            data = response.json()
            response.raise_for_status()
        except HTTPError as exc:
            self._handle_httperror(exc, data)
        except Timeout as exc:
            self._handle_timeout(exc)
        except JSONDecodeError as exc:
            self._handle_jsondecodeerror(exc, response)
        except Exception as exc:
            self._handle_unexpected(exc, response)

        return data
