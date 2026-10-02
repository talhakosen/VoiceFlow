"""Dikte eval seti — doğru metni yazmak için yerel düzeltme sayfası.

Sadece 127.0.0.1'de çalışır; ses ve metin bilgisayardan çıkmaz.
Her kaydet işlemi references.jsonl'e yazılır — istediğin an bırak, kaldığın
yerden devam eder.

Kullanım: python3 ml/eval/label_server.py   →  http://127.0.0.1:8780
"""
import json
import mimetypes
import os
import re
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
CLIPS = HERE / "clips.jsonl"
REFS = HERE / "references.jsonl"
AUDIO = HERE / "audio"
PAGE = HERE / "label_page.html"
PORT = 8780


def load_clips() -> list[dict]:
    return [json.loads(line) for line in CLIPS.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_refs() -> dict[str, dict]:
    if not REFS.exists():
        return {}
    refs = [json.loads(line) for line in REFS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {r["id"]: r for r in refs}


def save_ref(ref: dict) -> None:
    """Rewrite atomically — a crash mid-write must not lose earlier labels."""
    refs = load_refs()
    refs[ref["id"]] = ref
    fd, tmp = tempfile.mkstemp(dir=HERE, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        for r in refs.values():
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    os.replace(tmp, REFS)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args) -> None:  # sessiz
        pass

    def _send(self, code: int, body: bytes, ctype: str, extra: dict | None = None) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _send_audio(self, f: Path) -> None:
        """Range desteği şart: yoksa tarayıcı sesin ortasına atlayamıyor,
        her sürüklemede baştan çalıyor."""
        data = f.read_bytes()
        ctype = mimetypes.guess_type(f.name)[0] or "audio/wav"
        m = re.match(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if not m or (not m.group(1) and not m.group(2)):
            return self._send(200, data, ctype, {"Accept-Ranges": "bytes"})
        size = len(data)
        if m.group(1):
            start, end = int(m.group(1)), int(m.group(2)) if m.group(2) else size - 1
        else:  # "bytes=-N" → son N bayt
            start, end = max(0, size - int(m.group(2))), size - 1
        end = min(end, size - 1)
        if start > end:
            return self._send(416, b"", ctype, {"Content-Range": f"bytes */{size}"})
        self._send(206, data[start:end + 1], ctype,
                   {"Accept-Ranges": "bytes", "Content-Range": f"bytes {start}-{end}/{size}"})

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        if self.path == "/":
            self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/clips":
            self._json({"clips": load_clips(), "refs": load_refs()})
        elif self.path.startswith("/audio/"):
            f = (AUDIO / Path(self.path[len("/audio/"):]).name)  # .name → dizin dışına çıkılamaz
            if not f.is_file():
                return self._json({"error": "yok"}, 404)
            self._send_audio(f)
        else:
            self._json({"error": "yok"}, 404)

    def do_POST(self) -> None:
        if self.path != "/api/label":
            return self._json({"error": "yok"}, 404)
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        ids = {c["id"] for c in load_clips()}
        if body.get("id") not in ids or body.get("status") not in ("ok", "skip"):
            return self._json({"error": "geçersiz"}, 400)
        save_ref({
            "id": body["id"],
            "status": body["status"],
            "reference": (body.get("reference") or "").strip(),
            "edited": bool(body.get("edited")),  # ön-doldurma değişti mi (yanlılık analizi için)
        })
        self._json({"ok": True})


if __name__ == "__main__":
    print(f"Düzeltme sayfası: http://127.0.0.1:{PORT}  (durdurmak: Ctrl+C)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
