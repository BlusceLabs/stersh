from __future__ import annotations

import base64
import logging
from typing import Any

logger = logging.getLogger(__name__)

_BASE64_ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/="


def rc4(data: bytes, key: str | bytes) -> bytes:
    if isinstance(key, str):
        key = key.encode("utf-8")
    S = list(range(256))
    j = 0
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    i = j = 0
    out = bytearray()
    for byte in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(byte ^ S[(S[i] + S[j]) % 256])
    return bytes(out)


def custom_b64_decode(encoded: str) -> str:
    chars = []
    buffer = 0
    bits_collected = 0
    for ch in encoded:
        idx = _BASE64_ALPHABET.find(ch)
        if idx == -1:
            continue
        buffer = (buffer << 6) | idx
        bits_collected += 6
        if bits_collected >= 8:
            bits_collected -= 8
            chars.append((buffer >> bits_collected) & 0xFF)
            buffer &= (1 << bits_collected) - 1
    raw = bytes(chars).decode("latin-1")
    encoded_uri = "".join(f"%{b:02x}" for b in raw.encode("latin-1"))
    from urllib.parse import unquote
    return unquote(encoded_uri)


def decode_string_table_entry(
    entry: str,
    key: str | bytes | None = None,
    salt: str = "",
) -> str:
    decoded = custom_b64_decode(entry)
    if key is not None:
        decrypted = rc4(decoded.encode("latin-1"), key)
        decoded = decrypted.decode("latin-1")
    return decoded
