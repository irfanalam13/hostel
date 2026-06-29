"""Generate a VAPID keypair for Web Push.

    python manage.py vapid_keys

Prints the two values to put in your environment:

    NEXT_PUBLIC_VAPID_PUBLIC_KEY  -> browser applicationServerKey (frontend)
    VAPID_PRIVATE_KEY             -> backend only (NEVER expose to the browser)

The public key is the base64url-encoded uncompressed EC P-256 point the browser
expects; the private key is the base64url(DER PKCS8) form that
``Vapid01.from_string`` / ``pywebpush`` accept directly.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Generate a VAPID public/private keypair for Web Push."

    def handle(self, *args, **options):
        try:
            from cryptography.hazmat.primitives.serialization import (
                Encoding,
                NoEncryption,
                PrivateFormat,
                PublicFormat,
            )
            from py_vapid import Vapid01
            from py_vapid.utils import b64urlencode
        except ImportError as exc:  # pragma: no cover
            self.stderr.write(self.style.ERROR(f"pywebpush/py_vapid not installed: {exc}"))
            return

        vapid = Vapid01()
        vapid.generate_keys()

        public_key = b64urlencode(
            vapid.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
        )
        private_key = b64urlencode(
            vapid.private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
        )

        self.stdout.write(self.style.SUCCESS("VAPID keypair generated.\n"))
        self.stdout.write("Add these to your environment (.env):\n")
        self.stdout.write(self.style.HTTP_INFO(f"NEXT_PUBLIC_VAPID_PUBLIC_KEY={public_key}"))
        self.stdout.write(self.style.HTTP_INFO(f"VAPID_PRIVATE_KEY={private_key}"))
        self.stdout.write("VAPID_SUBJECT=mailto:admin@yourdomain.com\n")
        self.stdout.write(
            self.style.WARNING("Keep VAPID_PRIVATE_KEY secret — server-side only.")
        )
