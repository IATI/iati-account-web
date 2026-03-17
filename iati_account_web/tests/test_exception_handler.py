from django.test import TestCase
from iati_account_web.exceptions_middleware import IATIAccountExceptionHandlerMiddleware


class ExceptionHandlerTestCase(TestCase):
    def setUp(self):
        self.handler = IATIAccountExceptionHandlerMiddleware(lambda x: None)

    def test_tracking_code_length(self):
        # Check range of times from 1970-01-02 to 2040-01-01.
        for t in [86400000, 1735693200000, 1893459600000, 2051226000000, 2208992400000]:
            with self.subTest():
                self.assertEqual(len(self.handler._generate_error_tracking_code(time_ms=t)), 19)

    def test_tracking_code_early_date_zero_padding(self):
        # Check zero-padding of 1970-01-02.
        self.assertEqual(self.handler._generate_error_tracking_code(time_ms=86400000)[0:2], "00")

    def test_tracking_codes_have_invertible_times(self):
        for t in [1735693200000, 1893459600000, 2051226000000, 2208992400000, 86400000]:
            with self.subTest():
                tracking_code = self.handler._generate_error_tracking_code(t)
                tracking_code_time = tracking_code[0:4] + tracking_code[5:9]
                self.assertEqual(int(tracking_code_time, 36), t)
