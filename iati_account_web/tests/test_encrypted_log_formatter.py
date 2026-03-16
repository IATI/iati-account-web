import logging

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from django.test import TestCase
from iati_account_web.audit_log_formatter import EncryptedFormatter, decode_and_decrypt_log_entry


class EncryptedLogFormatterTestCase(TestCase):
    def setUp(self):
        # Generate a private/public key pair for testing - the key is serialised
        # to a buffer so it can be read by the formatter.
        self.PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.PUBLIC_KEY_BYTES = self.PRIVATE_KEY.public_key().public_bytes(
            encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        TEST_RECORDS = [
            (logging.INFO, "This is an audit log message that requires encrypting"),
            (logging.FATAL, "This is another audit log message that requires encrypting"),
            (logging.WARNING, "Another message with some b64 encoded data IufqSLfAe/oIZnad8zABqCB8k"),
        ]

        enc_formatter = EncryptedFormatter(public_key=self.PUBLIC_KEY_BYTES, fmt="%(levelname)s - %(message)s")
        normal_formatter = logging.Formatter(fmt="%(levelname)s - %(message)s")

        # For each test case we make the logging record, pass the record through
        # both the encrypted and normal log formatters, and store in the test data list.
        self.TEST_DATA = []
        for test_case in TEST_RECORDS:
            log_record = logging.LogRecord("test-logger", test_case[0], "", 0, test_case[1], None, None, None, None)
            self.TEST_DATA.append((enc_formatter.format(log_record), normal_formatter.format(log_record)))

    def test_log_formatter(self) -> None:
        """Test encryption and decryption of log messages"""

        for encrypted_entry, original_entry in self.TEST_DATA:
            decrypted_message = decode_and_decrypt_log_entry(encrypted_entry, self.PRIVATE_KEY)
            self.assertEqual(decrypted_message, original_entry)
