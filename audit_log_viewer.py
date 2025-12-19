import argparse
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from iati_account_web.audit_log_formatter import decode_and_decrypt_log_entry


def main():
    parser = argparse.ArgumentParser(
        prog="IATI Account Audit Log Viewer",
        description="Decrypts IATI Account audit log entries",
    )
    parser.add_argument("private_key", action="store", help="Private key for decryption")
    parser.add_argument(
        "-f", "--file", action="store", help="Log file to parse, otherwise parses from stdin", default=""
    )
    args = parser.parse_args()

    private_key_bytes = None

    with open(args.private_key, "rb") as private_key_fh:
        private_key_bytes = private_key_fh.read()

    private_key = serialization.load_pem_private_key(private_key_bytes, None)
    if not isinstance(private_key, rsa.RSAPrivateKey):
        raise AssertionError("private_key not of expected type rsa.RSAPrivateKey")

    if args.file:
        fh = open(args.file, "r")
    else:
        fh = sys.stdin

    for line in fh:
        print(decode_and_decrypt_log_entry(line, private_key))


if __name__ == "__main__":
    main()
