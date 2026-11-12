"""Regression tests for the bundled PNG validator and output copy."""

import os
import struct
import tempfile
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch

import main


ASSET_PATH = Path(__file__).with_name("entry.png")


def make_chunk(chunk_type: bytes, data: bytes = b"") -> bytes:
    """Build a PNG chunk with its correct CRC."""
    checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)


class MainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name)
        self.source_bytes = ASSET_PATH.read_bytes()

    def write_candidate(self, contents: bytes) -> Path:
        candidate = self.temp_path / "candidate.png"
        candidate.write_bytes(contents)
        return candidate

    def test_original_entry_png_passes_validation(self) -> None:
        self.assertEqual(main.load_image(ASSET_PATH), self.source_bytes)

    def test_unknown_critical_chunk_is_rejected(self) -> None:
        # A PNG signature and 25-byte IHDR chunk occupy the first 33 bytes.
        unknown_chunk = make_chunk(b"ABCD", b"unsupported")
        candidate = self.write_candidate(
            self.source_bytes[:33] + unknown_chunk + self.source_bytes[33:]
        )

        with self.assertRaisesRegex(ValueError, "unknown critical PNG chunk"):
            main.load_image(candidate)

    def test_invalid_png_crc_is_rejected(self) -> None:
        damaged = bytearray(self.source_bytes)
        offset = len(main.PNG_SIGNATURE)
        while offset < len(damaged):
            length = struct.unpack_from(">I", damaged, offset)[0]
            chunk_type = bytes(damaged[offset + 4:offset + 8])
            if chunk_type == b"IDAT":
                crc_offset = offset + 8 + length
                damaged[crc_offset] ^= 0x01
                break
            offset += 12 + length
        else:
            self.fail("bundled PNG contains no IDAT chunk")

        candidate = self.write_candidate(bytes(damaged))
        with self.assertRaisesRegex(ValueError, "bad checksum"):
            main.load_image(candidate)

    def test_missing_iend_is_rejected(self) -> None:
        candidate = self.write_candidate(self.source_bytes[:-12])

        with self.assertRaisesRegex(ValueError, "no complete PNG end chunk"):
            main.load_image(candidate)

    def test_output_copy_is_byte_for_byte_identical(self) -> None:
        with patch.dict(os.environ, {"MAKEFUN_OUTPUT_DIR": str(self.temp_path)}):
            main.main()

        self.assertEqual((self.temp_path / "entry.png").read_bytes(), self.source_bytes)


if __name__ == "__main__":
    unittest.main()
