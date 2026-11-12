"""Write the bundled cutest-picture asset to the competition output path."""

import os
import struct
import tempfile
import zlib
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_IMAGE_BYTES = 1024 * 1024
MAX_DIMENSION = 1024


def load_image(path: Path) -> bytes:
    """Read the fixed asset and reject files outside the contest limits."""
    image = path.read_bytes()
    if len(image) > MAX_IMAGE_BYTES:
        raise ValueError("entry.png exceeds the 1 MiB limit")
    if len(image) < 24 or image[:8] != PNG_SIGNATURE:
        raise ValueError("entry.png is not a complete PNG")

    width, height = struct.unpack_from(">II", image, 16)
    if not 0 < width <= MAX_DIMENSION or not 0 < height <= MAX_DIMENSION:
        raise ValueError("entry.png dimensions exceed 1024 by 1024")

    verify_png_chunks(image)
    return image


def verify_png_chunks(image: bytes) -> None:
    """Check each PNG chunk checksum and require a complete terminal IEND."""
    offset = len(PNG_SIGNATURE)
    saw_iend = False

    while offset < len(image):
        if offset + 12 > len(image):
            raise ValueError("entry.png ends inside a PNG chunk")

        chunk_length = struct.unpack_from(">I", image, offset)[0]
        chunk_type_start = offset + 4
        data_start = offset + 8
        chunk_end = data_start + chunk_length + 4
        if chunk_end > len(image):
            raise ValueError("entry.png contains a truncated PNG chunk")

        chunk_type = image[chunk_type_start:data_start]
        expected_crc = struct.unpack_from(">I", image, data_start + chunk_length)[0]
        actual_crc = zlib.crc32(image[chunk_type_start:data_start + chunk_length])
        if actual_crc != expected_crc:
            raise ValueError("entry.png contains a PNG chunk with a bad checksum")

        offset = chunk_end
        if chunk_type == b"IEND":
            if chunk_length != 0 or offset != len(image):
                raise ValueError("entry.png has an invalid PNG end chunk")
            saw_iend = True
            break

    if not saw_iend:
        raise ValueError("entry.png has no complete PNG end chunk")


def main() -> None:
    asset = Path(__file__).with_name("entry.png")
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "entry.png"
    image = load_image(asset)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(dir=output_dir, prefix=".entry-", delete=False) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(image)
        temporary_path.replace(destination)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


if __name__ == "__main__":
    main()
