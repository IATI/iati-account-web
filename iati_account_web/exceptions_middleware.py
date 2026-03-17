import logging
import secrets
import string
import time
import traceback

from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.template.response import TemplateResponse
from iati_account_web.exceptions import (
    RegisterYourData404,
    RegisterYourDataBadRequest,
    RegisterYourDataPermissionDenied,
    RegisterYourDataResponseParsingIssue,
    RegisterYourDataServerIssue,
)

app_logger = logging.getLogger("iati_account")
audit_logger = logging.getLogger("audit")


class IATIAccountExceptionHandlerMiddleware:
    BASE36_CHARS = string.digits + string.ascii_uppercase
    BASE36_LEN = len(BASE36_CHARS)

    def __init__(self, get_response: callable):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse:  # noqa: C901
        """Map exceptions to standard HTTP responses

        Parameters
        ----------
        request : HttpRequest
            Request associated with the raised exception.
        exception : Exception
            Exception that was raised.

        Returns
        -------
        HttpResponse
        """
        stack_trace = traceback.format_exc()

        # Generate tracking code to help end users report problems that we can then identify in logs.
        tracking = self._generate_error_tracking_code()

        # Log the exception.  If the user was logged in we also put this in the audit log.
        app_logger.error(
            f"Exception {type(exception).__name__}: {exception} raised on page {request.path} with "
            f"tracking code {tracking}. Stack trace: {stack_trace}"
        )
        if request.user.oidc_sub:
            audit_logger.error(
                f"Exception {exception} raised on page {request.path} for "
                f"user {request.user.log_label} with tracking code {tracking}"
            )

        # Respond to the exceptions.
        if isinstance(exception, RegisterYourDataResponseParsingIssue):
            return TemplateResponse(request, "errors/internal.html", {"tracking": tracking})

        if isinstance(exception, RegisterYourDataServerIssue):
            return TemplateResponse(request, "errors/internal.html", {"tracking": tracking})

        if isinstance(exception, RegisterYourDataBadRequest):
            return TemplateResponse(request, "errors/internal.html", {"tracking": tracking})

        if isinstance(exception, RegisterYourDataPermissionDenied):
            return TemplateResponse(request, "errors/permission_denied.html", {"tracking": tracking})

        if isinstance(exception, RegisterYourData404):
            return TemplateResponse(request, "errors/404.html", {"tracking": tracking})

        if isinstance(exception, PermissionDenied):
            return TemplateResponse(request, "errors/permission_denied.html", {"tracking": tracking})

        return TemplateResponse(request, "errors/unknown.html", {"tracking": tracking})

    def _generate_error_tracking_code(self, time_ms: int | None = None) -> str:
        """Generate a simple error tracking code for logs/end users.

        This code is a base-36 encoded integer time in milliseconds and some
        additional random characters to produce a 16 character string.  In
        the future we could add information from the requests, e.g., to identify
        the view function or endpoint.  For now we present this code to the end
        user and add it to our logs.

        See also: https://en.wikipedia.org/wiki/Base36

        Returns
        -------
        str
        """

        # Get time in (ms) since epoch and convert to BASE36.
        if time_ms is None:
            time_ms = int(time.time()) * 1000
        if time_ms == 0:
            return f"{self.BASE36_CHARS[0]*4}-{self.BASE36_CHARS[0]*4}"

        tracking_code = ""
        while time_ms > 0:
            remainder = time_ms % self.BASE36_LEN
            tracking_code = self.BASE36_CHARS[remainder] + tracking_code
            time_ms //= self.BASE36_LEN

        # If the time part of the code is less than 8 characters then zero pad.
        padding = "0" * (8 - len(tracking_code)) if len(tracking_code) < 8 else ""
        tracking_code = padding + tracking_code

        # Add extra characters to make the code 16 characters long.
        tracking_code += "".join(secrets.choice(self.BASE36_CHARS) for i in range(16 - len(tracking_code)))

        # Separate into 4 character blocks.
        return "-".join([tracking_code[x : x + 4] for x in range(0, 16, 4)])
