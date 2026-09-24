"""Read bounded PE/ELF metadata without loading or executing the sample."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

MAX_SAMPLE = 512 * 1024 * 1024


def sample_digest(path):
    digest = hashlib.sha256()
    total = 0
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            total += len(chunk)
            if total > MAX_SAMPLE:
                raise ValueError("Sample exceeds the 512 MiB profiling limit")
            digest.update(chunk)
    return digest.hexdigest()


def read_at(stream, offset, count, size):
    if offset < 0 or count < 0 or offset + count > size:
        raise ValueError("Header points outside the file")
    stream.seek(offset)
    data = stream.read(count)
    if len(data) != count:
        raise ValueError("File changed or header is truncated")
    return data


def clr_metadata(directory, rva_bytes):
    rva, length = struct.unpack("<II", directory)
    if not rva and not length:
        return {}
    if not rva or length < 72:
        raise ValueError("Malformed CLR directory")
    clr = rva_bytes(rva, 72)
    cb, _, _, metadata_rva, metadata_size, clr_flags = struct.unpack_from("<IHHIII", clr)
    if cb < 72 or cb > length or metadata_size < 16:
        raise ValueError("Invalid CLR header or metadata extent")
    # Check the metadata endpoints without retaining a potentially large blob.
    signature = rva_bytes(metadata_rva, 4)
    rva_bytes(metadata_rva + metadata_size - 1, 1)
    if signature != b"BSJB":
        raise ValueError("CLR metadata signature missing")
    return {"kind": "managed" if clr_flags & 1 else "managed-or-mixed", "clr": True,
            "clr_flags": hex(clr_flags), "metadata_rva": hex(metadata_rva)}


def pe_metadata(stream, size):
    dos = read_at(stream, 0, 64, size)
    offset = struct.unpack_from("<I", dos, 60)[0]
    header = read_at(stream, offset, 24, size)
    if header[:4] != b"PE\0\0":
        raise ValueError("Invalid PE signature")
    machine, sections = struct.unpack_from("<HH", header, 4)
    optional_size, flags = struct.unpack_from("<HH", header, 20)
    if not 1 <= sections <= 96:
        raise ValueError("Unsupported section count")
    optional = read_at(stream, offset + 24, optional_size, size)
    magic = struct.unpack_from("<H", optional)[0]
    if magic not in (0x10B, 0x20B):
        raise ValueError("Unsupported PE optional header")
    directory_offset = 96 if magic == 0x10B else 112
    if len(optional) < directory_offset:
        raise ValueError("Truncated optional header")
    count = struct.unpack_from("<I", optional, directory_offset - 4)[0]
    if count > (len(optional) - directory_offset) // 8:
        raise ValueError("Data directories exceed optional header")
    table = read_at(stream, offset + 24 + optional_size, sections * 40, size)
    headers_size = struct.unpack_from("<I", optional, 60)[0]

    def rva_bytes(rva, length):
        if rva < headers_size and rva + length <= headers_size:
            return read_at(stream, rva, length, size)
        matches = []
        for index in range(sections):
            _, base, raw_size, raw_offset = struct.unpack_from("<IIII", table, index * 40 + 8)
            if base <= rva and rva + length <= base + raw_size:
                matches.append(raw_offset + rva - base)
        if len(matches) != 1:
            raise ValueError("Unmapped or ambiguous CLR directory")
        return read_at(stream, matches[0], length, size)

    result = {"format": "PE", "bits": 32 if magic == 0x10B else 64,
              "architecture": {0x14C: "x86", 0x8664: "x64", 0xAA64: "arm64", 0x1C4: "arm"}.get(machine, hex(machine)),
              "dll": bool(flags & 0x2000), "kind": "native", "clr": False}
    if count > 14:
        result.update(clr_metadata(optional[directory_offset + 14 * 8:directory_offset + 15 * 8], rva_bytes))
    return result


def elf_metadata(stream, size):
    identity = read_at(stream, 0, 16, size)
    if identity[4] not in (1, 2) or identity[5] not in (1, 2) or identity[6] != 1:
        raise ValueError("Invalid ELF class, endian or version")
    header = read_at(stream, 0, 52 if identity[4] == 1 else 64, size)
    endian = "<" if identity[5] == 1 else ">"
    file_type, machine = struct.unpack_from(endian + "HH", header, 16)
    return {"format": "ELF", "bits": 32 if identity[4] == 1 else 64, "kind": "native",
            "architecture": {3: "x86", 62: "x64", 40: "arm", 183: "arm64", 243: "riscv"}.get(machine, str(machine)),
            "elf_type": file_type, "endian": "little" if identity[5] == 1 else "big"}


def profile(path, expected_sha256=None):
    path = Path(path).resolve(strict=True)
    before = path.stat()
    digest = sample_digest(path)
    if expected_sha256 and digest != expected_sha256:
        raise ValueError("Sample hash changed since entry planning; bind the new sample version")
    result = {"path": str(path), "sha256": digest, "size": before.st_size,
              "kind": "unknown", "format": "unknown", "executed_sample": False}
    with path.open("rb") as stream:
        signature = stream.read(4)
        try:
            if signature.startswith(b"MZ"):
                result.update(pe_metadata(stream, before.st_size))
            elif signature == b"\x7fELF":
                result.update(elf_metadata(stream, before.st_size))
            else:
                result["reason"] = "Unrecognized format; extension is not a classifier"
        except (ValueError, struct.error) as exc:
            result.update(kind="unknown", reason=str(exc))
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns) or sample_digest(path) != digest:
        raise ValueError("Sample changed while profiling; no stable result")
    result["feature_hints"] = (["sample.binary", "binary.profiled", "binary.managed"] if result["kind"].startswith("managed")
                               else ["sample.binary", "binary.profiled", "binary.native"] if result["kind"] == "native"
                               else ["sample.binary", "binary.unknown"])
    result["limits"] = "Header classification only; no loader validation, unpacking, decompilation or runtime verdict"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sample")
    parser.add_argument("--expected-sha256")
    args = parser.parse_args()
    try:
        print(json.dumps(profile(args.sample, args.expected_sha256), ensure_ascii=False, indent=2))
    except (ValueError, OSError) as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
