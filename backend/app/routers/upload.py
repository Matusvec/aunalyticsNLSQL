"""
POST /api/upload — store .sqlite / .db / .csv / .json in backend/db (CSV/JSON → SQLite via pandas).
GET /api/databases — list available .db / .sqlite files for the database picker.

Hardened against:
- Overwrite of existing databases
- Memory exhaustion via large CSV/JSON (chunked + row cap)
- Disguised payloads (SQLite header byte check)
- Body size limits (settings.max_upload_bytes)
"""

from __future__ import annotations

import io
import json
import logging
import re
import sqlite3
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.rate_limit import rate
from app.settings import get_settings


router = APIRouter()
logger = logging.getLogger(__name__)
_settings = get_settings()

ALLOWED_EXTENSIONS = {".sqlite", ".db", ".csv", ".json"}
SQLITE_MAGIC = b"SQLite format 3\x00"
CSV_CHUNK_ROWS = 50_000


def sanitize_filename(name: str) -> str:
    name = Path(name).name
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    cleaned = cleaned.lstrip(".") or "uploaded"
    return cleaned


def table_name_from_filename(name: str) -> str:
    stem = Path(name).stem
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", stem)
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"t_{cleaned}" if cleaned else "uploaded"
    return cleaned


def ensure_db_dir() -> Path:
    db_dir = get_settings().db_dir
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


def _refuse_overwrite(dest: Path) -> None:
    if dest.exists():
        raise HTTPException(
            status_code=409,
            detail=f"A database named {dest.name!r} already exists. Rename your file or delete the existing one.",
        )


async def _read_capped(file: UploadFile, max_bytes: int) -> bytes:
    """Read the upload while enforcing the max byte limit.

    UploadFile.read(N) returns up to N bytes; we read max_bytes+1 so we can detect overflow.
    """
    chunk = await file.read(max_bytes + 1)
    if len(chunk) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {max_bytes} bytes allowed.",
        )
    return chunk


def _validate_sqlite_payload(content: bytes) -> None:
    if not content.startswith(SQLITE_MAGIC):
        raise HTTPException(
            status_code=400,
            detail="File does not look like a SQLite database (missing magic header).",
        )


def _atomic_save(dest: Path, content: bytes) -> None:
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        tmp.write_bytes(content)
        tmp.replace(dest)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _stream_csv_to_sqlite(content: bytes, dest: Path, table_name: str, row_cap: int) -> None:
    """Stream CSV → SQLite in chunks so large files don't blow up RAM."""
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    rows_written = 0
    try:
        if tmp.exists():
            tmp.unlink()
        conn = sqlite3.connect(str(tmp))
        try:
            buf = io.BytesIO(content)
            reader = pd.read_csv(buf, chunksize=CSV_CHUNK_ROWS)
            first = True
            for chunk in reader:
                if rows_written + len(chunk) > row_cap:
                    raise HTTPException(
                        status_code=413,
                        detail=f"CSV exceeds the row cap of {row_cap} rows.",
                    )
                chunk.to_sql(
                    table_name,
                    conn,
                    if_exists="replace" if first else "append",
                    index=False,
                )
                rows_written += len(chunk)
                first = False
            if rows_written == 0:
                raise HTTPException(status_code=400, detail="CSV had no rows.")
        finally:
            conn.close()
        tmp.replace(dest)
    except HTTPException:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
    except pd.errors.EmptyDataError as exc:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="CSV appears empty or invalid.") from exc
    except Exception:
        logger.exception("CSV → SQLite conversion failed")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="CSV could not be converted.") from None


def _stream_json_to_sqlite(content: bytes, dest: Path, table_name: str, row_cap: int) -> None:
    """JSON → SQLite. Requires a top-level array of records; rejects nested structures."""
    try:
        decoded = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="JSON is not valid UTF-8 / JSON.") from exc

    if not isinstance(decoded, list):
        raise HTTPException(
            status_code=400,
            detail="JSON must be a top-level array of records (objects).",
        )
    if not decoded:
        raise HTTPException(status_code=400, detail="JSON array is empty.")
    if len(decoded) > row_cap:
        raise HTTPException(
            status_code=413,
            detail=f"JSON exceeds the row cap of {row_cap} rows.",
        )
    if not all(isinstance(item, dict) for item in decoded):
        raise HTTPException(
            status_code=400,
            detail="Every JSON record must be an object.",
        )

    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        if tmp.exists():
            tmp.unlink()
        df = pd.DataFrame(decoded)
        conn = sqlite3.connect(str(tmp))
        try:
            df.to_sql(table_name, conn, if_exists="replace", index=False)
        finally:
            conn.close()
        tmp.replace(dest)
    except HTTPException:
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise
    except Exception:
        logger.exception("JSON → SQLite conversion failed")
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="JSON could not be converted.") from None


@router.get("/databases")
def list_databases() -> dict:
    """List SQLite files in the configured DB dir for the UI database picker."""
    db_dir = ensure_db_dir()
    out: list[dict] = []
    for p in sorted(db_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".db", ".sqlite"}:
            if p.name == "query_history.sqlite":
                continue
            try:
                st = p.stat()
            except OSError:
                continue
            out.append({"filename": p.name, "size_bytes": st.st_size})
    return {"databases": out}


@router.post("/upload")
@rate(_settings.rate_limit_upload)
async def upload_file(request: Request, file: UploadFile = File(...)) -> JSONResponse:
    settings = get_settings()
    max_bytes = settings.max_upload_bytes
    row_cap = settings.max_upload_rows

    filename = sanitize_filename(file.filename or "uploaded")
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file extension: {ext}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    content = await _read_capped(file, max_bytes)
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    db_dir = ensure_db_dir()
    stem = Path(filename).stem
    table_name = table_name_from_filename(filename)

    if ext in {".sqlite", ".db"}:
        _validate_sqlite_payload(content)
        dest_db = db_dir / filename
        _refuse_overwrite(dest_db)
        _atomic_save(dest_db, content)
        final_name = dest_db.name
    elif ext == ".csv":
        dest_db = db_dir / f"{stem}.sqlite"
        _refuse_overwrite(dest_db)
        _stream_csv_to_sqlite(content, dest_db, table_name, row_cap)
        final_name = dest_db.name
    elif ext == ".json":
        dest_db = db_dir / f"{stem}.sqlite"
        _refuse_overwrite(dest_db)
        _stream_json_to_sqlite(content, dest_db, table_name, row_cap)
        final_name = dest_db.name
    else:
        raise HTTPException(status_code=415, detail="Unsupported file type")

    return JSONResponse(
        status_code=201,
        content={"success": True, "filename": final_name},
    )
