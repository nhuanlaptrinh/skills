#!/usr/bin/env python3
"""Convert a text document to one verified MP3 through the GiongAI API."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


DEFAULT_API_BASE_URL = "https://api.giongai.cloud/v1"
DEFAULT_PROVIDER = "minimax"
DEFAULT_MODEL_ID = "speech-2.8-turbo"
DEFAULT_LANGUAGE_CODE = "Vietnamese"
DEFAULT_CHUNK_CHARS = 4200
DEFAULT_TIMEOUT_SECONDS = 600
MAX_INPUT_BYTES = 10 * 1024 * 1024
MAX_TEXT_CHARS = 200_000
MAX_AUDIO_BYTES = 80 * 1024 * 1024
SUPPORTED_EXTENSIONS = {
    ".txt",
    ".md",
    ".csv",
    ".json",
    ".srt",
    ".vtt",
    ".html",
    ".htm",
    ".xml",
    ".docx",
}
SUCCESS_STATES = {"completed", "complete", "success", "succeeded", "done", "finished"}
FAILURE_STATES = {"failed", "failure", "error", "cancelled", "canceled"}


class TTSFailure(RuntimeError):
    """An actionable, safe-to-display conversion failure."""


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_value(values: dict[str, str], *names: str, default: str = "") -> str:
    for name in names:
        process_value = os.environ.get(name, "").strip()
        if process_value:
            return process_value
        config_value = values.get(name, "").strip()
        if config_value:
            return config_value
    return default


def merged_config(config_path: Path | None) -> dict[str, str]:
    config = load_env(config_path) if config_path else {}
    source_path_raw = env_value(config, "GIONGAI_ENV_SOURCE", "VOICE_ENV_FILE")
    source = load_env(Path(source_path_raw).expanduser()) if source_path_raw else {}
    source.update(config)
    return source


def read_secret(values: dict[str, str]) -> str:
    direct = env_value(values, "GIONGAI_API_KEY", "VOICE_API_KEY")
    if direct:
        return direct
    key_file = env_value(values, "GIONGAI_API_KEY_FILE")
    if not key_file:
        return ""
    key_name = env_value(values, "GIONGAI_API_KEY_NAME", default="GIONGAI_API_KEY")
    file_values = load_env(Path(key_file).expanduser())
    return file_values.get(key_name, "").strip()


def resolve_settings(config_path: Path | None) -> dict[str, Any]:
    values = merged_config(config_path)
    api_key = read_secret(values)
    voice_id = env_value(values, "GIONGAI_VOICE_ID", "VOICE_API_VOICE_ID")
    if not api_key:
        raise TTSFailure(
            "Thiếu API key GiongAI. Cấu hình GIONGAI_API_KEY hoặc GIONGAI_API_KEY_FILE trong env server-side."
        )
    if not voice_id:
        raise TTSFailure("Thiếu GIONGAI_VOICE_ID; không được tự đoán voice ID.")
    try:
        chunk_chars = int(env_value(values, "GIONGAI_CHUNK_CHARS", default=str(DEFAULT_CHUNK_CHARS)))
        timeout_seconds = float(
            env_value(values, "GIONGAI_TIMEOUT_SECONDS", default=str(DEFAULT_TIMEOUT_SECONDS))
        )
        speed = float(env_value(values, "GIONGAI_SPEED", default="1.0"))
        pitch = int(env_value(values, "GIONGAI_PITCH", default="0"))
        volume = float(env_value(values, "GIONGAI_VOLUME", default="1.0"))
    except ValueError as exc:
        raise TTSFailure("Thông số GiongAI trong env không hợp lệ.") from exc
    if not 1000 <= chunk_chars <= 5000:
        raise TTSFailure("GIONGAI_CHUNK_CHARS phải nằm trong khoảng 1000..5000.")
    if timeout_seconds < 10 or timeout_seconds > 3600:
        raise TTSFailure("GIONGAI_TIMEOUT_SECONDS phải nằm trong khoảng 10..3600.")
    base_url = env_value(
        values,
        "GIONGAI_API_BASE_URL",
        "VOICE_API_BASE_URL",
        default=DEFAULT_API_BASE_URL,
    ).rstrip("/")
    auth_mode = env_value(values, "GIONGAI_AUTH_MODE", default="xi-api-key").lower()
    if auth_mode not in {"xi-api-key", "bearer"}:
        raise TTSFailure("GIONGAI_AUTH_MODE chỉ nhận xi-api-key hoặc bearer.")
    return {
        "api_key": api_key,
        "api_base_url": base_url,
        "auth_mode": auth_mode,
        "voice_id": voice_id,
        "provider": env_value(values, "GIONGAI_PROVIDER", "VOICE_API_PROVIDER", default=DEFAULT_PROVIDER),
        "model_id": env_value(
            values,
            "GIONGAI_MODEL_ID",
            "VOICE_API_MODEL_ID",
            default=DEFAULT_MODEL_ID,
        ),
        "language_code": env_value(
            values,
            "GIONGAI_LANGUAGE_CODE",
            default=DEFAULT_LANGUAGE_CODE,
        ),
        "speed": speed,
        "pitch": pitch,
        "volume": volume,
        "chunk_chars": chunk_chars,
        "timeout_seconds": timeout_seconds,
    }


def api_url(settings: dict[str, Any], path: str) -> str:
    parsed = urllib.parse.urlsplit(settings["api_base_url"])
    if parsed.scheme != "https" or not parsed.netloc:
        raise TTSFailure("GIONGAI_API_BASE_URL phải là một URL HTTPS hợp lệ.")
    base_path = parsed.path.rstrip("/")
    if not base_path.endswith("/v1"):
        base_path += "/v1"
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, f"{base_path}/{path.lstrip('/')}", "", "")
    )


def parse_response(raw: bytes, content_type: str) -> Any:
    if "json" not in content_type.lower():
        return raw
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TTSFailure("GiongAI trả về JSON không hợp lệ.") from exc


def safe_error(payload: Any, status: int) -> str:
    if isinstance(payload, dict):
        for key in ("error", "detail", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                nested = value.get("message") or value.get("detail") or value.get("error")
                if nested:
                    return str(nested)
    return f"GiongAI trả về lỗi HTTP {status}."


class GiongAIClient:
    def __init__(self, settings: dict[str, Any]) -> None:
        self.settings = settings

    def request(self, method: str, path: str, body: dict[str, Any] | None = None, idempotency_key: str = "") -> Any:
        headers = {
            "Accept": "application/json",
            "User-Agent": "OpenClaw-TextFileToMp3/1.0",
        }
        if self.settings["auth_mode"] == "bearer":
            headers["Authorization"] = f"Bearer {self.settings['api_key']}"
        else:
            headers["xi-api-key"] = self.settings["api_key"]
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            api_url(self.settings, path),
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return parse_response(response.read(), response.headers.get("Content-Type", ""))
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                payload = parse_response(raw, exc.headers.get("Content-Type", ""))
            except TTSFailure:
                payload = None
            raise TTSFailure(safe_error(payload, exc.code)) from exc
        except urllib.error.URLError as exc:
            raise TTSFailure(f"Không thể kết nối GiongAI: {exc.reason}") from exc

    def doctor(self) -> None:
        self.request("GET", "/auth/me")

    def submit(self, text: str, request_key: str) -> Any:
        body: dict[str, Any] = {
            "text": text,
            "provider": self.settings["provider"],
            "model_id": self.settings["model_id"],
            "language_code": self.settings["language_code"],
            "voice_settings": {"speed": self.settings["speed"]},
            "export_transcript": False,
        }
        if self.settings["provider"].lower() == "minimax":
            body["voice_settings"].update(
                {"pitch": self.settings["pitch"], "vol": self.settings["volume"]}
            )
        voice_path = urllib.parse.quote(self.settings["voice_id"], safe="")
        return self.request(
            "POST",
            f"/text-to-speech/{voice_path}",
            body,
            idempotency_key=request_key,
        )

    def history(self, task_id: str) -> Any:
        return self.request("GET", f"/history/{urllib.parse.quote(task_id, safe='')}")


def recursive_values(payload: Any, wanted_keys: set[str]) -> list[Any]:
    found: list[Any] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key.lower() in wanted_keys:
                found.append(value)
            found.extend(recursive_values(value, wanted_keys))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(recursive_values(item, wanted_keys))
    return found


def first_string(payload: Any, keys: set[str]) -> str:
    for value in recursive_values(payload, keys):
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def audio_url_from(payload: Any) -> str:
    value = first_string(
        payload,
        {"audio_url", "audiourl", "download_url", "downloadurl", "file_url", "fileurl"},
    )
    if value:
        return value
    return ""


def task_id_from(payload: Any) -> str:
    return first_string(payload, {"task_id", "taskid", "request_id", "requestid", "id"})


def status_from(payload: Any) -> str:
    value = first_string(payload, {"status", "state"})
    return value.lower().strip() if value else ""


def error_from(payload: Any) -> str:
    return first_string(payload, {"error", "detail_error", "detailerror", "message"})


def download_audio(url: str, destination: Path) -> None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise TTSFailure("GiongAI trả về audio URL không an toàn.")
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "OpenClaw-TextFileToMp3/1.0"})
        with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
            total = 0
            while True:
                block = response.read(64 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_AUDIO_BYTES:
                    raise TTSFailure("Audio trả về vượt giới hạn 80 MiB.")
                output.write(block)
        if temporary.stat().st_size == 0:
            raise TTSFailure("GiongAI trả về audio rỗng.")
        temporary.replace(destination)
    except urllib.error.HTTPError as exc:
        raise TTSFailure(f"Không tải được audio, HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise TTSFailure(f"Không tải được audio: {exc.reason}") from exc
    finally:
        temporary.unlink(missing_ok=True)


def synthesize_chunk(
    client: GiongAIClient,
    text: str,
    destination: Path,
    request_key: str,
    timeout_seconds: float,
) -> str:
    submitted = client.submit(text, request_key)
    if isinstance(submitted, (bytes, bytearray)):
        destination.write_bytes(submitted)
        return ""
    audio_url = audio_url_from(submitted)
    task_id = task_id_from(submitted)
    if not audio_url and not task_id:
        raise TTSFailure("GiongAI không trả về task ID hoặc audio URL.")
    detail = submitted
    deadline = time.monotonic() + timeout_seconds
    while not audio_url and time.monotonic() < deadline:
        time.sleep(1.0)
        detail = client.history(task_id)
        audio_url = audio_url_from(detail)
        state = status_from(detail)
        if state in FAILURE_STATES:
            raise TTSFailure(error_from(detail) or "GiongAI tạo audio thất bại.")
        if state in SUCCESS_STATES and not audio_url:
            raise TTSFailure("GiongAI báo hoàn tất nhưng không trả về audio URL.")
    if not audio_url:
        raise TTSFailure(f"GiongAI chưa hoàn tất sau {int(timeout_seconds)} giây.")
    download_audio(audio_url, destination)
    return task_id


def read_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            xml_data = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile, OSError) as exc:
        raise TTSFailure("File DOCX không hợp lệ hoặc không đọc được.") from exc
    try:
        root = ElementTree.fromstring(xml_data)
    except ElementTree.ParseError as exc:
        raise TTSFailure("Nội dung DOCX không hợp lệ.") from exc
    paragraphs: list[str] = []
    for paragraph in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"):
        text = "".join(
            node.text or ""
            for node in paragraph.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t")
        ).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def decode_text(raw: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16", "cp1258"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def clean_text(text: str, suffix: str) -> str:
    if "\x00" in text:
        raise TTSFailure("File chứa byte nhị phân, không phải file văn bản hợp lệ.")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if suffix in {".srt", ".vtt"}:
        filtered: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.upper() == "WEBVTT":
                continue
            if stripped.isdigit() or re.match(r"^\d{1,2}:\d{2}:\d{2}[,.]\d{3}\s+-->\s+", stripped):
                continue
            filtered.append(stripped)
        text = "\n".join(filtered)
    elif suffix in {".md", ".html", ".htm", ".xml"}:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", text)
        text = re.sub(r"[`*_>#]+", " ", text)
        text = re.sub(r"^\s*[-+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    if not text:
        raise TTSFailure("File không có nội dung văn bản để đọc.")
    if len(text) > MAX_TEXT_CHARS:
        raise TTSFailure("Nội dung sau khi trích xuất vượt giới hạn 200.000 ký tự; hãy chia nhỏ file.")
    return text


def read_input(path: Path) -> tuple[str, str]:
    path = path.expanduser().resolve()
    if not path.is_file():
        raise TTSFailure("Không tìm thấy file đầu vào.")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise TTSFailure("File đầu vào vượt giới hạn 10 MiB.")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise TTSFailure(f"Định dạng {suffix or '(không có đuôi)'} chưa được hỗ trợ.")
    text = read_docx(path) if suffix == ".docx" else decode_text(path.read_bytes())
    return clean_text(text, suffix), path.name


def split_text(text: str, limit: int) -> list[str]:
    if len(text) <= limit:
        return [text]
    units = [unit.strip() for unit in re.split(r"\n{2,}", text) if unit.strip()]
    chunks: list[str] = []
    current = ""
    for unit in units:
        pieces = [unit]
        if len(unit) > limit:
            pieces = [piece.strip() for piece in re.split(r"(?<=[.!?。！？])\s+", unit) if piece.strip()]
        for piece in pieces:
            while len(piece) > limit:
                split_at = piece.rfind(" ", 0, limit + 1)
                split_at = split_at if split_at >= limit // 2 else limit
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(piece[:split_at].strip())
                piece = piece[split_at:].strip()
            candidate = f"{current}\n\n{piece}" if current else piece
            if len(candidate) <= limit:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = piece
    if current:
        chunks.append(current)
    return [chunk for chunk in chunks if chunk]


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    result = re.sub(r"[^A-Za-z0-9._-]+", "-", ascii_value).strip("-._")
    return result[:80] or "text-to-mp3"


def verify_mp3(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise TTSFailure("File MP3 đầu ra không tồn tại hoặc rỗng.")
    if not shutil.which("ffprobe"):
        raise TTSFailure("Thiếu ffprobe; hãy cài ffmpeg trên máy này.")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise TTSFailure("File đầu ra không phải MP3 hợp lệ.")


def merge_audio(parts: list[Path], output: Path, temporary_dir: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if len(parts) == 1:
        shutil.copyfile(parts[0], output)
        verify_mp3(output)
        return
    if not shutil.which("ffmpeg"):
        raise TTSFailure("Thiếu ffmpeg để nối các phần audio.")
    concat_list = temporary_dir / "concat.txt"
    lines = []
    for part in parts:
        escaped = str(part.resolve()).replace("'", "'\\''")
        lines.append(f"file '{escaped}'")
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")
    result = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-vn",
            "-map_metadata",
            "-1",
            "-c:a",
            "libmp3lame",
            "-q:a",
            "2",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise TTSFailure("Không thể nối các phần audio thành MP3.")
    verify_mp3(output)


def convert(args: argparse.Namespace) -> dict[str, Any]:
    settings = resolve_settings(Path(args.config).expanduser() if args.config else None)
    if args.voice_id.strip():
        settings["voice_id"] = args.voice_id.strip()
    text, input_name = read_input(Path(args.input))
    input_path = Path(args.input).expanduser().resolve()
    input_digest = hashlib.sha256(input_path.read_bytes()).hexdigest()
    render_descriptor = json.dumps(
        {
            "input_sha256": input_digest,
            "voice_id": settings["voice_id"],
            "provider": settings["provider"],
            "model_id": settings["model_id"],
            "language_code": settings["language_code"],
            "speed": settings["speed"],
            "pitch": settings["pitch"],
            "volume": settings["volume"],
            "chunk_chars": settings["chunk_chars"],
        },
        sort_keys=True,
    ).encode("utf-8")
    render_digest = hashlib.sha256(render_descriptor).hexdigest()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{slugify(Path(input_name).stem)}_{render_digest[:12]}.mp3"
    if output.exists() and not args.force:
        verify_mp3(output)
        return {
            "status": "reused",
            "output": str(output),
            "chunks": 0,
            "input_sha256": input_digest,
        }
    chunks = split_text(text, settings["chunk_chars"])
    request_prefix = args.request_key.strip() or f"local:{render_digest[:24]}"
    client = GiongAIClient(settings)
    with tempfile.TemporaryDirectory(prefix=f"text-to-mp3-{render_digest[:10]}-") as temp_name:
        temporary_dir = Path(temp_name)
        parts: list[Path] = []
        task_ids: list[str] = []
        for index, chunk in enumerate(chunks, start=1):
            part = temporary_dir / f"part-{index:04d}.mp3"
            task_id = synthesize_chunk(
                client,
                chunk,
                part,
                f"{request_prefix}:{render_digest[:16]}:{index}",
                settings["timeout_seconds"],
            )
            verify_mp3(part)
            parts.append(part)
            if task_id:
                task_ids.append(task_id)
        merge_audio(parts, output, temporary_dir)
    return {
        "status": "completed",
        "output": str(output),
        "chunks": len(chunks),
        "input_sha256": input_digest,
        "task_ids": task_ids,
    }


def self_test(input_path: Path) -> dict[str, Any]:
    text, input_name = read_input(input_path)
    chunks = split_text(text, DEFAULT_CHUNK_CHARS)
    return {
        "status": "self-test-ok",
        "input": input_name,
        "characters": len(text),
        "chunks": len(chunks),
        "max_chunk_characters": max(len(chunk) for chunk in chunks),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a text file to MP3 with GiongAI")
    parser.add_argument("--config", default="", help="Server-side runtime env file")
    parser.add_argument("--input", help="Exact inbound text file")
    parser.add_argument("--output-dir", default="./media", help="Directory for the final MP3")
    parser.add_argument("--request-key", default="", help="Stable current inbound request key")
    parser.add_argument("--voice-id", default="", help="Override configured voice ID")
    parser.add_argument("--force", action="store_true", help="Regenerate even if the digest output exists")
    parser.add_argument("--doctor", action="store_true", help="Check authentication without creating audio")
    parser.add_argument("--self-test", action="store_true", help="Validate a file without calling the API")
    args = parser.parse_args()
    if args.doctor and (args.input or args.self_test):
        parser.error("--doctor cannot be combined with --input or --self-test")
    if not args.doctor and not args.input:
        parser.error("Cần --input, hoặc dùng riêng --doctor")
    try:
        if args.doctor:
            settings = resolve_settings(Path(args.config).expanduser() if args.config else None)
            GiongAIClient(settings).doctor()
            result = {"status": "doctor-ok", "auth_mode": settings["auth_mode"], "api_base_url": settings["api_base_url"]}
        elif args.self_test:
            result = self_test(Path(args.input))
        else:
            result = convert(args)
    except (OSError, TTSFailure, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
