import base64
import logging
from datetime import datetime

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_public_key


class EncryptedFormatter(logging.Formatter):
    """Formatter for Python Logging objects that encrypts the log contents"""

    def __init__(self, *args, public_key: str = None, **kwargs) -> None:
        """Setup the formatter"""
        super().__init__(*args, **kwargs)

        # Load PEM public key from provided filename.
        try:
            self._public_key = load_pem_public_key(public_key)
            if not isinstance(self._public_key, rsa.RSAPublicKey):
                raise RuntimeError("Audit log public key not RSA")
        except Exception as exc:
            raise RuntimeError(f"Cannot load public key for audit log with error {exc}")

        # Generate a symmetric key for this instance and setup the symmetric cipher.
        self._symmetric_key = Fernet.generate_key()
        self._fernet = Fernet(self._symmetric_key)

        # Encrypt the symmetric key and base-64 encode for logging.
        self._enc_sym_key = self._public_key.encrypt(
            self._symmetric_key,
            padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        )
        self._enc_sym_key_b64 = base64.b64encode(self._enc_sym_key).decode("utf-8")

    def _encrypt(self, plain_text: str) -> str:
        """Use symmetric encryption to encrypt a log string.

        Parameters
        ----------
        plain_text : str
            Plain text log string to encrypt.

        Returns
        -------
        str
            Ciphertext
        """
        ciphertext = self._fernet.encrypt(plain_text.encode(encoding="utf-8"))
        return base64.b64encode(ciphertext).decode(encoding="utf-8")

    def format(self, record: logging.LogRecord) -> str:
        """Format and encrypt a log string.

        Parameters
        ----------
        record : logging.LogRecord
            Log record to format and encrypt

        Returns
        -------
        str
            Encrypted log string.
        """
        log_entry = super().format(record)
        log_time = datetime.fromtimestamp(record.created)
        return f"{log_time.isoformat()} {self._enc_sym_key_b64} {self._encrypt(log_entry)}"


def decode_and_decrypt_log_entry(
    encrypted_log_entry: str, private_key: rsa.RSAPrivateKey
) -> tuple[datetime, str, str]:
    """Extract the log entry time, symmetric encryption key and encrypted data from an encrypted log entry

    Parameters
    ----------
    encrypted_log_entry : str
        Encrypted log entry to parse.
    private_key : rsa.RSAPrivateKey
        Private key to decrypt the symmetric encryption key.

    Returns
    -------
    str
        Decrypted message.
    """

    # Parse the encrypted log entry.
    record_time, encrypted_sym_key, encrypted_data = encrypted_log_entry.split(" ")

    # Decrypt the symmetric key.
    symmetric_key = private_key.decrypt(
        base64.b64decode(encrypted_sym_key),
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
    ).decode("utf-8")

    # Decrypt the log entry.
    fernet = Fernet(symmetric_key)
    message = fernet.decrypt(base64.b64decode(encrypted_data)).decode("utf-8")

    return message
