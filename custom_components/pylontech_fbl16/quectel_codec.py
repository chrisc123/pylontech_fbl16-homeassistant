"""Quectel Custom BLE Protocol Codec (Mode A).

Decodes advertisement manufacturer bytes, derives AES-128 session keys,
handles garbling/splicing (byte stuffing), and parses Quectel TTLV packets.
"""

from __future__ import annotations

import hashlib
import logging
import struct
from typing import Any, NamedTuple

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

_LOGGER = logging.getLogger(__name__)


class QuecBleAdvInfo(NamedTuple):
    """Parsed Quectel advertisement broadcast information."""

    tag: str
    version: int
    pk: str
    dk: str
    status: int
    flags: int


def parse_quec_manufacturer_bytes(data: bytes) -> QuecBleAdvInfo | None:
    """Parses raw Quectel BLE advertisement data starting with b'QUEC'."""
    if len(data) < 21 or data[:4] != b"QUEC":
        return None
    try:
        tag = data[0:4].decode("utf-8", errors="replace")
        version = struct.unpack(">h", data[4:6])[0]
        pk_len = data[6]
        pk_end = 7 + pk_len
        pk = data[7:pk_end].decode("utf-8", errors="replace")
        dk_len = data[pk_end]
        dk_start = pk_end + 1
        dk_end = dk_start + dk_len
        dk = data[dk_start:dk_end].hex().upper()
        status = data[dk_end]
        flags_hi_idx = pk_len + 10 + dk_len
        flags = (data[flags_hi_idx] << 8) | data[flags_hi_idx + 1] if len(data) >= flags_hi_idx + 2 else 0
        return QuecBleAdvInfo(tag, version, pk, dk, status, flags)
    except Exception as exc:
        _LOGGER.debug("Failed parsing Quectel advertisement bytes: %s", exc)
        return None


def extract_quec_info_from_manufacturer_data(manufacturer_data: dict[int, bytes]) -> QuecBleAdvInfo | None:
    """Extracts Quectel advertisement info from Bleak's split manufacturer_data dict.

    In Bleak/Home Assistant, AD Type 0xFF has its first 2 bytes used as the dict key (little-endian uint16),
    and the remaining bytes as data. For b'QUEC' (0x51, 0x55, 0x45, 0x43):
    company_id = 0x5551 (21841) and data = b'EC...'
    """
    for company_id, data in manufacturer_data.items():
        reconstructed = company_id.to_bytes(2, "little") + data
        if reconstructed.startswith(b"QUEC"):
            info = parse_quec_manufacturer_bytes(reconstructed)
            if info:
                return info
        if data.startswith(b"QUEC"):
            info = parse_quec_manufacturer_bytes(data)
            if info:
                return info
    return None


def derive_quectel_session(dk: str, random_str: str) -> tuple[str, str, bytes, bytes]:
    """Derives AES session key & IV matching QuecCustomBleChannel.java:

    strHash = SHA256(dk.upper()).hex_lowercase()
    bindingKey = strHash[:32]
    authToken = SHA256(f"{bindingKey};{random_str}").hex_lowercase()
    aesKey = bytes.fromhex(bindingKey)
    aesIv = random_str.encode('utf-8')
    """
    clean_dk = dk.strip().upper()
    full_dk_hash = hashlib.sha256(clean_dk.encode("utf-8")).hexdigest().lower()
    binding_key = full_dk_hash[: len(full_dk_hash) // 2]
    auth_token = hashlib.sha256(f"{binding_key};{random_str}".encode("utf-8")).hexdigest().lower()
    aes_key = bytes.fromhex(binding_key)
    aes_iv = random_str.encode("utf-8")
    return binding_key, auth_token, aes_key, aes_iv


def aes_cbc_encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    """Encrypts plaintext with AES-128-CBC and PKCS7 padding."""
    padder = padding.PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def aes_cbc_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    """Decrypts ciphertext with AES-128-CBC and PKCS7 unpadding."""
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


def garble_buffer(buf: bytes) -> bytes:
    """Escapes 0xAA with 0x55 matching EncodeTools.garbleBuffer."""
    out = bytearray()
    for b in buf:
        out.append(b)
        if b == 0xAA:
            out.append(0x55)
    return bytes(out)


def splice_buffer(buf: bytes) -> bytes:
    """Removes stuffed 0x55 following 0xAA matching DecodeTools.spliceBuffer."""
    out = bytearray()
    i = 0
    n = len(buf)
    while i < n:
        b = buf[i]
        out.append(b)
        if b == 0xAA and (i + 1) < n and buf[i + 1] == 0x55:
            i += 2
        else:
            i += 1
    return bytes(out)


def build_quec_frame(
    cmd: int,
    payload: bytes = b"",
    packet_id: int = 1,
    aes_key: bytes | None = None,
    aes_iv: bytes | None = None,
) -> bytes:
    """Builds a complete Quectel 0xAAAA frame with byte stuffing and optional AES-128 encryption."""
    body = aes_cbc_encrypt(payload, aes_key, aes_iv) if (aes_key and aes_iv) else payload
    length = len(body) + 5
    tail = struct.pack(">HH", packet_id & 0xFFFF, cmd & 0xFFFF) + body
    checksum = sum(tail) & 0xFF
    after_header = struct.pack(">HB", length, checksum) + tail
    return b"\xAA\xAA" + garble_buffer(after_header)


def encode_ttlv_binary(ttlv_id: int, value: bytes) -> bytes:
    """Encodes a TTLV element with type=3 (bytes/UTF-8 string)."""
    header = ((ttlv_id & 0x1FFF) << 3) | 0x03
    return struct.pack(">HH", header, len(value)) + value


def parse_ttlv_items(data: bytes, offset: int = 0, max_items: int | None = None) -> tuple[dict[int, Any], int]:
    """Recursively decodes Quectel TTLV items according to DecodeTools.parsePayload:
      - type 0/1: Boolean
      - type 2: Number with sign, scale exponent, and byte_len (DecodeTools meta byte)
      - type 3/5: Raw bytes or UTF-8 string
      - type 4: Nested Struct containing 'count' TTLV items
    """
    items: dict[int, Any] = {}
    n = len(data)
    count = 0
    while offset + 2 <= n:
        if max_items is not None and count >= max_items:
            break
        header = struct.unpack(">H", data[offset : offset + 2])[0]
        offset += 2
        ttlv_id = (header >> 3) & 0x1FFF
        ttlv_type = header & 0x07
        count += 1

        if ttlv_type in (0, 1):
            items[ttlv_id] = bool(ttlv_type == 1)
        elif ttlv_type in (3, 5):
            if offset + 2 > n:
                break
            length = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2
            val_bytes = data[offset : offset + length]
            offset += length
            try:
                decoded_str = val_bytes.decode("utf-8")
                if all(c.isprintable() or c in "\r\n\t " for c in decoded_str):
                    items[ttlv_id] = decoded_str
                else:
                    items[ttlv_id] = val_bytes
            except Exception:
                items[ttlv_id] = val_bytes
        elif ttlv_type == 2:
            if offset >= n:
                break
            meta = data[offset]
            offset += 1
            sign = (meta >> 7) & 1
            scale = (meta >> 3) & 0x0F
            byte_len = (meta & 0x07) + 1
            if offset + byte_len > n:
                break
            val_bytes = data[offset : offset + byte_len]
            offset += byte_len
            val = int.from_bytes(val_bytes, "big", signed=False)
            if sign > 0:
                val = -val
            if scale > 0:
                items[ttlv_id] = val / (10 ** scale)
            else:
                items[ttlv_id] = val
        elif ttlv_type == 4:
            if offset + 2 > n:
                break
            cnt = struct.unpack(">H", data[offset : offset + 2])[0]
            offset += 2
            sub_items, offset = parse_ttlv_items(data, offset=offset, max_items=cnt)
            items[ttlv_id] = sub_items
        else:
            break
    return items, offset


def decode_ttlv_payload(payload: bytes) -> dict[int, Any]:
    """Decodes a top-level TTLV byte stream."""
    items, _ = parse_ttlv_items(payload, offset=0)
    return items


class QuectelFrameStreamParser:
    """Assembles and decodes incoming notification chunks across BLE MTU boundaries."""

    def __init__(self) -> None:
        self.raw_buf = bytearray()
        self.aes_key: bytes | None = None
        self.aes_iv: bytes | None = None

    def set_encryption(self, key: bytes, iv: bytes) -> None:
        self.aes_key = key
        self.aes_iv = iv

    def feed(self, chunk: bytes) -> list[tuple[int, int, bytes]]:
        """Feeds raw BLE bytes and returns a list of (packet_id, cmd, decrypted_payload)."""
        self.raw_buf.extend(chunk)
        frames: list[tuple[int, int, bytes]] = []

        while True:
            idx = self.raw_buf.find(b"\xAA\xAA")
            if idx == -1:
                if self.raw_buf.endswith(b"\xAA"):
                    del self.raw_buf[:-1]
                else:
                    self.raw_buf.clear()
                break
            if idx > 0:
                del self.raw_buf[:idx]

            # raw_buf starts with b"\xAA\xAA"
            unstuffed = bytearray(b"\xAA\xAA")
            raw_idx = 2
            n = len(self.raw_buf)
            expected_unstuffed_len: int | None = None
            found = False

            while raw_idx < n:
                b = self.raw_buf[raw_idx]
                unstuffed.append(b)
                raw_idx += 1
                if b == 0xAA and raw_idx < n and self.raw_buf[raw_idx] == 0x55:
                    raw_idx += 1

                if expected_unstuffed_len is None and len(unstuffed) >= 4:
                    payload_len = struct.unpack(">H", unstuffed[2:4])[0]
                    expected_unstuffed_len = payload_len + 4

                if expected_unstuffed_len is not None and len(unstuffed) >= expected_unstuffed_len:
                    found = True
                    break

            if not found:
                break

            # Consume the exact raw bytes corresponding to this unstuffed frame
            del self.raw_buf[:raw_idx]
            frame = bytes(unstuffed[:expected_unstuffed_len])

            expected_cs = frame[4]
            calc_cs = sum(frame[5:]) & 0xFF
            if expected_cs != calc_cs:
                _LOGGER.warning("Quectel checksum mismatch: expected 0x%02X, got 0x%02X", expected_cs, calc_cs)
                continue

            packet_id, cmd = struct.unpack(">HH", frame[5:9])
            raw_payload = frame[9:]
            if self.aes_key and self.aes_iv and len(raw_payload) > 0:
                try:
                    payload = aes_cbc_decrypt(raw_payload, self.aes_key, self.aes_iv)
                except Exception as exc:
                    _LOGGER.error("AES decrypt failed for cmd 0x%04X: %s", cmd, exc)
                    continue
            else:
                payload = raw_payload

            frames.append((packet_id, cmd, payload))

        return frames
