"""Stdlib HTTP dapp server for ClosedIntelligence."""

from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .core import Lens, answer
from .dapp import CompanyField, EmployeeIdentity

STATIC_DIR = Path(__file__).with_name("static")


class DappRequestHandler(BaseHTTPRequestHandler):
    server: "DappServer"

    def do_HEAD(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_file_headers(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/app.js":
            self._send_file_headers(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if path == "/style.css":
            self._send_file_headers(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            return
        self.send_response(HTTPStatus.NOT_FOUND.value)
        self.end_headers()

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self._send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return
        if path == "/app.js":
            self._send_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return
        if path == "/style.css":
            self._send_file(STATIC_DIR / "style.css", "text/css; charset=utf-8")
            return
        if path == "/api/state":
            self._send_json(self.server.field.snapshot().to_dict())
            return
        if path == "/api/bundle":
            self._send_json(self.server.field.export_bundle())
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/api/employee":
                employee = EmployeeIdentity.create(
                    str(body["handle"]),
                    str(body.get("display_name") or body["handle"]),
                    str(body.get("department") or "general"),
                )
                event = self.server.field.join_employee(employee)
                self.server.persist()
                self._send_json({"event": event.to_dict(), "employee": employee.to_dict()})
                return
            if path == "/api/knowledge":
                event = self.server.field.post_knowledge(
                    str(body["author"]),
                    str(body["title"]),
                    str(body["body"]),
                    body.get("tags") or (),
                )
                self.server.persist()
                self._send_json({"event": event.to_dict()})
                return
            if path == "/api/proposal":
                event = self.server.field.open_proposal(
                    str(body["author"]),
                    str(body["title"]),
                    str(body["body"]),
                    body.get("options") or ("yes", "no"),
                )
                self.server.persist()
                self._send_json({"event": event.to_dict()})
                return
            if path == "/api/vote":
                event = self.server.field.vote(
                    str(body["author"]),
                    str(body["proposal_id"]),
                    str(body["option"]),
                    str(body.get("reason") or ""),
                )
                self.server.persist()
                self._send_json({"event": event.to_dict()})
                return
            if path == "/api/task":
                event = self.server.field.assign_task(
                    str(body["author"]),
                    str(body["assignee"]),
                    str(body["title"]),
                    str(body["body"]),
                    str(body.get("due") or ""),
                )
                self.server.persist()
                self._send_json({"event": event.to_dict()})
                return
            if path == "/api/decision":
                event = self.server.field.record_decision(
                    str(body["author"]),
                    str(body["title"]),
                    str(body["body"]),
                    str(body.get("proposal_id") or ""),
                )
                self.server.persist()
                self._send_json({"event": event.to_dict()})
                return
            if path == "/api/answer":
                lens = Lens.from_mapping(self.server.field.to_lens_records(), source="company-field")
                packet = answer(str(body["question"]), lens)
                self._send_json(packet.to_dict())
                return
            if path == "/api/merge":
                report = self.server.field.merge_bundle(body)
                self.server.persist()
                self._send_json(report.to_dict())
                return
        except Exception as exc:
            self._send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        self._send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, fmt: str, *args: Any) -> None:
        if self.server.quiet:
            return
        super().log_message(fmt, *args)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("content-length") or "0")
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("content-type", "application/json; charset=utf-8")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_file(self, path: Path, content_type: str) -> None:
        data = path.read_bytes()
        self._send_file_headers(path, content_type, len(data))
        self.wfile.write(data)

    def _send_file_headers(self, path: Path, content_type: str, length: int | None = None) -> None:
        size = path.stat().st_size if length is None else length
        self.send_response(HTTPStatus.OK.value)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(size))
        self.end_headers()


class DappServer(ThreadingHTTPServer):
    def __init__(self, addr: tuple[str, int], field: CompanyField, state_path: Path, *, quiet: bool = False):
        super().__init__(addr, DappRequestHandler)
        self.field = field
        self.state_path = state_path
        self.quiet = quiet

    def persist(self) -> None:
        self.field.save(self.state_path)


def serve(host: str, port: int, state_path: str | Path, *, company: str, mesh_key: str | None = None, quiet: bool = False) -> DappServer:
    field = CompanyField.load(state_path, company=company, mesh_key=mesh_key)
    server = DappServer((host, port), field, Path(state_path), quiet=quiet)
    server.persist()
    return server
