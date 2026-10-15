"""Read the exact supplied data bytes, rejecting changes before any fitting."""

from hashlib import sha256
from io import BytesIO
from pathlib import Path

from .dataset import Dataset, read_votes


EXPECTED_DATA_SHA256 = "c58ba145070415d084950fe8a80c517fd14e05d3285e371338a66791cee5de94"


def read_frozen_votes(path: str | Path) -> tuple[Dataset, str]:
    payload = Path(path).read_bytes()
    digest = sha256(payload).hexdigest()
    if digest != EXPECTED_DATA_SHA256:
        raise ValueError(f"Frozen data SHA-256 mismatch: expected {EXPECTED_DATA_SHA256}, got {digest}. STOP.")
    # The reader consumes the bytes that were checked, rather than reopening the path.
    return read_votes(BytesIO(payload)), digest
