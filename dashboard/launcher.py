from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
MUJOCO_HTML = DASHBOARD / "mujoco.html"


def _read_entries() -> dict[str, dict[str, Any]]:
    html = MUJOCO_HTML.read_text(encoding="utf-8")
    marker = "const MUJOCO_ENTRIES = {"
    start = html.index(marker) + len(marker)
    end = html.index("\n};", start)
    block = html[start:end]

    entries: dict[str, dict[str, Any]] = {}
    entry_re = re.compile(r"\n\s*'?([A-Za-z0-9.]+)'?\s*:\s*\{(.*?)\n\s*\}", re.S)
    field_re = re.compile(r"(folder|view|simulate)\s*:\s*(?:'([^']+)'|\[([^\]]*)\])", re.S)
    string_re = re.compile(r"'([^']+)'")

    for match in entry_re.finditer(block):
      version_id = match.group(1)
      body = match.group(2)
      entry: dict[str, Any] = {"view": [], "simulate": []}

      for field in field_re.finditer(body):
        key, scalar, array_body = field.groups()
        if scalar is not None:
          entry[key] = scalar
        else:
          entry[key] = string_re.findall(array_body or "")

      if entry.get("folder"):
        entries[version_id] = entry

    return entries


MUJOCO_ENTRIES = _read_entries()


def _json_response(handler: SimpleHTTPRequestHandler, status: HTTPStatus, data: dict[str, Any]) -> None:
    payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _resolve_launch(version_id: str, script: str) -> tuple[Path, Path]:
    entry = MUJOCO_ENTRIES.get(version_id)
    if not entry:
      raise ValueError("未登记该版本的 MuJoCo 入口")

    allowed = set(entry.get("view", [])) | set(entry.get("simulate", []))
    if script not in allowed:
      raise ValueError("该脚本不在可启动白名单中")

    script_path = Path(script)
    if script_path.is_absolute() or ".." in script_path.parts:
      raise ValueError("脚本路径不合法")
    if script_path.suffix.lower() != ".py":
      raise ValueError("只能启动 Python 脚本")
    if not script_path.name.startswith(("view_", "simulate_")):
      raise ValueError("只能直接启动查看或仿真脚本")

    folder = str(entry["folder"])
    folder_path = (ROOT / folder).resolve()
    file_path = (folder_path / script_path).resolve()
    if ROOT.resolve() not in file_path.parents:
      raise ValueError("脚本必须位于项目目录内")
    if folder_path not in file_path.parents and file_path.parent != folder_path:
      raise ValueError("脚本必须位于版本目录内")
    if not file_path.exists():
      raise FileNotFoundError("脚本文件不存在")

    return folder_path, file_path


def _launch(version_id: str, script: str) -> dict[str, Any]:
    folder_path, file_path = _resolve_launch(version_id, script)
    creationflags = 0
    if os.name == "nt":
      creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

    process = subprocess.Popen(
      [sys.executable, str(file_path)],
      cwd=str(folder_path),
      stdout=subprocess.DEVNULL,
      stderr=subprocess.DEVNULL,
      stdin=subprocess.DEVNULL,
      close_fds=False,
      creationflags=creationflags,
    )
    return {
      "ok": True,
      "pid": process.pid,
      "version": version_id,
      "script": script,
      "path": str(file_path),
    }


class LauncherHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
      super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self) -> None:
      self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
      self.send_header("Pragma", "no-cache")
      self.send_header("Expires", "0")
      super().end_headers()

    def do_GET(self) -> None:
      if self.path.startswith("/api/health"):
        _json_response(self, HTTPStatus.OK, {"ok": True, "launcher": "mujoco-local", "root": str(ROOT)})
        return
      super().do_GET()

    def do_POST(self) -> None:
      if not self.path.startswith("/api/launch"):
        _json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "未知接口"})
        return

      try:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body or "{}")
        version_id = str(payload.get("id", ""))
        script = str(payload.get("script", ""))
        result = _launch(version_id, script)
        _json_response(self, HTTPStatus.OK, result)
      except (FileNotFoundError, ValueError) as exc:
        _json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": str(exc)})
      except Exception as exc:
        _json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Local MuJoCo launcher dashboard server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), LauncherHandler)
    print(f"MuJoCo launcher listening on http://{args.host}:{args.port}/dashboard/index.html")
    server.serve_forever()


if __name__ == "__main__":
    main()
