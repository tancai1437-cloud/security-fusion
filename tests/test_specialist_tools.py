"""Real loopback controls and binary metadata; generated headers/logs are synthetic fixtures."""
import base64
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from fusion_binary_profile import profile
from fusion_crash_triage import triage
from fusion_proxy_probe import BODY_LIMIT, probe


def pe_fixture(managed=False, mixed=False, bits=64):
    """Minimal synthetic header only; not a runnable PE or managed assembly."""
    blob = bytearray(1024)
    blob[:2] = b"MZ"
    struct.pack_into("<I", blob, 60, 128)
    blob[128:132] = b"PE\0\0"
    optional_size = 240 if bits == 64 else 224
    struct.pack_into("<HH", blob, 132, 0x8664 if bits == 64 else 0x14C, 1)
    struct.pack_into("<HH", blob, 148, optional_size, 0x2002)
    struct.pack_into("<H", blob, 152, 0x20B if bits == 64 else 0x10B)
    struct.pack_into("<I", blob, 212, 512)
    directory = 112 if bits == 64 else 96
    struct.pack_into("<I", blob, 152 + directory - 4, 16)
    section = 152 + optional_size
    struct.pack_into("<IIII", blob, section + 8, 512, 0x2000, 512, 512)
    if managed:
        struct.pack_into("<II", blob, 152 + directory + 14 * 8, 0x2000, 72)
        struct.pack_into("<IHHIII", blob, 512, 72, 2, 5, 0x2080, 32, 0 if mixed else 1)
        blob[640:644] = b"BSJB"
    return blob


@contextmanager
def proxy_fixture():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            marker = self.headers.get("X-Forwarded-For")
            requests.append((self.path, marker))
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/should-not-follow")
                body = b"redirect only"
            else:
                self.send_response(200)
                # This fixture exposes diagnostic IP only, never an authorization bypass.
                ip = marker.split(",")[0] if self.path == "/trusts-client" and marker else self.client_address[0]
                body = (b"x" * (BODY_LIMIT + 1) if self.path == "/large" else
                        json.dumps({"selected_client_ip": ip, "protected_access": False}).encode())
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield "http://127.0.0.1:{}".format(server.server_port), requests
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)


class SpecialistToolTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="fusion-specialist-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def test_pe_dll_native_managed_mixed_and_pe32_are_distinct(self):
        path = self.root / "sample.dll"
        for bits in (32, 64):
            for managed, mixed, kind in ((False, False, "native"), (True, False, "managed"),
                                         (True, True, "managed-or-mixed")):
                with self.subTest(bits=bits, kind=kind):
                    path.write_bytes(pe_fixture(managed, mixed, bits))
                    result = profile(path)
                    self.assertEqual(result["kind"], kind)
                    self.assertEqual(result["bits"], bits)
                    self.assertTrue(result["dll"])
                    self.assertFalse(result["executed_sample"])

    def test_malformed_clr_and_disguised_text_never_route_as_native(self):
        path = self.root / "looks-managed.dll"
        malformed = pe_fixture(True)
        malformed[640:644] = b"NOPE"
        for blob in (malformed, b"MZ", b"not a dll", pe_fixture(True)[:530]):
            path.write_bytes(blob)
            result = profile(path)
            self.assertEqual(result["kind"], "unknown")
            self.assertNotIn("binary.native", result["feature_hints"])
        path.write_bytes(pe_fixture())
        digest = profile(path)["sha256"]
        path.write_bytes(pe_fixture(True))
        with self.assertRaisesRegex(ValueError, "hash changed"):
            profile(path, digest)

    def test_real_interpreter_is_read_without_execution(self):
        if sys.platform not in ("win32", "linux"):
            self.skipTest("PE/ELF fixture requires Windows or Linux")
        result = profile(sys.executable)
        self.assertEqual(result["kind"], "native")
        self.assertIn(result["format"], ("PE", "ELF"))
        self.assertFalse(result["executed_sample"])

    def test_elf_big_endian_and_truncation(self):
        path = self.root / "a.elf"
        blob = bytearray(64)
        blob[:7] = b"\x7fELF\x02\x02\x01"
        struct.pack_into(">HH", blob, 16, 3, 183)
        path.write_bytes(blob)
        self.assertEqual(profile(path)["architecture"], "arm64")
        path.write_bytes(blob[:25])
        self.assertEqual(profile(path)["kind"], "unknown")

    def test_proxy_controls_capture_real_headers_and_do_not_claim_bypass(self):
        with proxy_fixture() as (base, requests):
            for route, changed in (("/trusts-client", True), ("/ignores-client", False)):
                result = probe(base + route)
                bodies = [json.loads(base64.b64decode(r["body_base64"])) for r in result["requests"]]
                self.assertEqual(bodies[0]["selected_client_ip"] != bodies[1]["selected_client_ip"], changed)
                self.assertTrue(all(not b["protected_access"] for b in bodies))
                self.assertEqual(result["verdict"], "observations_only")
            self.assertEqual(len(requests), 6)
            self.assertEqual(requests[2][1], "192.0.2.17, 198.51.100.29")

    def test_proxy_does_not_follow_redirects_and_marks_partial_capture(self):
        with proxy_fixture() as (base, requests):
            result = probe(base + "/redirect")
            self.assertEqual([r["status"] for r in result["requests"]], [302] * 3)
            self.assertEqual([path for path, _ in requests], ["/redirect"] * 3)
            result = probe(base + "/large")
            self.assertTrue(all(r["truncated"] and r["captured_bytes"] == BODY_LIMIT for r in result["requests"]))
        for url in ("file:///tmp/file", "https://user:secret@example.invalid", "https://example.invalid/#x"):
            with self.assertRaises(ValueError):
                probe(url)

    def test_crash_classification_keeps_evidence_lines_and_unknown_is_not_safe(self):
        path = self.root / "synthetic.log"
        for diagnostic, classification in (("stack-buffer-overflow", "stack-buffer-overflow"),
                                            ("stack-overflow", "stack-exhaustion"),
                                            ("heap-use-after-free", "heap-use-after-free")):
            path.write_text("SYNTHETIC parser fixture\nERROR: AddressSanitizer: " + diagnostic +
                            "\n    #0 0x123 in controlled_fixture\n", encoding="utf-8")
            result = triage(path)
            self.assertEqual(result["classification"], [classification])
            self.assertEqual(result["diagnostics"][0]["line"], 2)
            self.assertEqual(result["frames"][0]["line"], 3)
            self.assertEqual(result["verdict"], "diagnostic_only")
        path.write_text("No recognizable diagnostic", encoding="utf-8")
        self.assertEqual(triage(path)["verdict"], "insufficient_evidence")

    def test_real_asan_positive_and_negative_control_when_compiler_available(self):
        compiler = shutil.which("clang") if sys.platform == "linux" else None
        if not compiler:
            if os.environ.get("GITHUB_ACTIONS") == "true" and sys.platform == "linux":
                self.fail("Linux CI must provide clang for the real sanitizer regression")
            self.skipTest("Real ASan regression requires Linux and existing clang; no compiler installed by test")
        source, binary = self.root / "controlled.c", self.root / "controlled"
        source.write_text("#include <stdlib.h>\nint main(int argc,char **argv) {\n"
                          "volatile unsigned char buffer[4]={0};\n"
                          "int index=argc>1?atoi(argv[1]):0; buffer[index]=1; return 0; }\n", encoding="utf-8")
        built = subprocess.run([compiler, "-g", "-O1", "-fsanitize=address", "-fno-omit-frame-pointer",
                                str(source), "-o", str(binary)], capture_output=True, timeout=30)
        self.assertEqual(built.returncode, 0, built.stderr.decode(errors="replace"))
        environment = dict(os.environ, ASAN_OPTIONS="detect_leaks=0:disable_coredump=1:abort_on_error=0")
        negative = subprocess.run([str(binary), "1"], env=environment, capture_output=True, timeout=10)
        positive = subprocess.run([str(binary), "8"], env=environment, capture_output=True, timeout=10)
        self.assertEqual(negative.returncode, 0, negative.stderr)
        self.assertNotEqual(positive.returncode, 0)
        log = self.root / "actual-asan.log"
        log.write_bytes(positive.stderr)
        self.assertIn("stack-buffer-overflow", triage(log)["classification"])
        self.assertEqual(profile(binary)["format"], "ELF")


if __name__ == "__main__":
    unittest.main()
