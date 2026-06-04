import os
import re
from pathlib import Path


EXT_MAP = {
    "python": ".py",
    "py": ".py",
    "javascript": ".js",
    "js": ".js",
    "typescript": ".ts",
    "ts": ".ts",
    "html": ".html",
    "css": ".css",
    "json": ".json",
    "markdown": ".md",
    "md": ".md",
    "text": ".txt",
    "txt": ".txt",
    "sql": ".sql",
    "bash": ".sh",
    "shell": ".sh",
    "powershell": ".ps1",
    "ps1": ".ps1",
}

LOCAL_URL_RE = re.compile(
    r"https?://(?:localhost|127(?:\.\d{1,3}){3}|\[::1\])(?::\d+)?(?:/[^\s`\"')<>\]]*)?",
    re.IGNORECASE,
)


def extract_local_urls(text: str) -> list[str]:
    """Return local preview URLs in first-seen order."""
    seen = set()
    urls = []
    for match in LOCAL_URL_RE.finditer(text or ""):
        url = match.group(0).rstrip(".,;，。；")
        if url not in seen:
            seen.add(url)
            urls.append(url)
    return urls


def _last_filename_hint(before_text: str):
    chunk = before_text[-600:]

    def last_match(pattern: str):
        matches = list(re.finditer(pattern, chunk, re.IGNORECASE))
        return matches[-1] if matches else None

    patterns = [
        r'[`「]([a-zA-Z0-9_\-./\\]+\.\w{1,10})[`」]',
        r'(?:#{1,5}\s*|\*\*\s*)([a-zA-Z0-9_\-./\\]+\.\w{1,10})',
        r'(?:创建|新建|保存|写入|文件|路径|file|create|save|path)\s*[:：]?\s*[`"\']?([a-zA-Z0-9_\-./\\]+\.\w{1,10})',
    ]
    for pattern in patterns:
        match = last_match(pattern)
        if match:
            return match.group(1)

    for line in reversed(chunk.splitlines()):
        match = re.match(r'^\s*(?:[-*]\s*)?([a-zA-Z0-9_\-./\\]+\.\w{1,10})\b', line)
        if match:
            return match.group(1)
    return None


def extract_code_blocks(response_text: str) -> list[dict]:
    """Extract markdown code blocks and infer target filenames when possible."""
    blocks = []
    text = response_text or ""
    for match in re.finditer(r"```([^\n`]*)\n(.*?)```", text, re.DOTALL):
        info = (match.group(1) or "").strip()
        code = (match.group(2) or "").strip()
        if not code or len(code) < 3:
            continue

        info_parts = info.split()
        lang = (info_parts[0] if info_parts else "").lower().strip()
        filename = None

        for part in info_parts[1:]:
            value = part.split("=", 1)[-1].strip("'\"")
            if re.search(r"\.\w{1,10}$", value):
                filename = value
                break

        if not filename:
            filename = _last_filename_hint(text[:match.start()])

        if not filename:
            ext = EXT_MAP.get(lang, f".{lang}" if lang else ".txt")
            filename = f"file_{len(blocks) + 1}{ext}"

        blocks.append({
            "filename": filename.replace("\\", "/").lstrip("/"),
            "lang": lang or "text",
            "code": code,
        })
    return blocks


def safe_code_target_path(target_dir: str, filename: str, index: int) -> tuple[str, str]:
    base_dir = Path(target_dir).expanduser().resolve()
    clean_name = (filename or f"file_{index + 1}.txt").replace("\\", "/").strip()
    clean_name = clean_name.lstrip("/")
    if re.match(r"^[a-zA-Z]:", clean_name):
        clean_name = os.path.basename(clean_name)
    clean_name = os.path.normpath(clean_name)
    if clean_name in ("", ".", "..") or clean_name.startswith(".." + os.sep):
        clean_name = os.path.basename(clean_name) or f"file_{index + 1}.txt"

    target_path = (base_dir / clean_name).resolve()
    if os.path.commonpath([str(base_dir), str(target_path)]) != str(base_dir):
        target_path = (base_dir / (os.path.basename(clean_name) or f"file_{index + 1}.txt")).resolve()

    rel_path = os.path.relpath(target_path, base_dir).replace("\\", "/")
    return str(target_path), rel_path


def save_code_blocks_to_dir(blocks: list[dict], target_dir: str) -> list[str]:
    Path(target_dir).mkdir(parents=True, exist_ok=True)
    saved_files = []
    used_paths = set()
    for index, block in enumerate(blocks):
        abs_path, rel_path = safe_code_target_path(target_dir, block.get("filename"), index)
        if rel_path in used_paths:
            stem, ext = os.path.splitext(rel_path)
            rel_path = f"{stem}_{index + 1}{ext}"
            abs_path = str((Path(target_dir).resolve() / rel_path).resolve())
        used_paths.add(rel_path)
        Path(abs_path).parent.mkdir(parents=True, exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(block.get("code") or "")
        saved_files.append(rel_path)
    return saved_files
