"""
POST /api/upload — store .sqlite / .db / .csv / .json in backend/db (CSV/JSON → SQLite via pandas).
GET /api/databases — list available .db / .sqlite files for the database picker.

Aligned with Task 5; used by the Week 2 file upload UI (Task 7).
"""

from __future__ import annotations

import io
import re
import sqlite3
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {".sqlite", ".db", ".csv", ".json"}


def sanitize_filename(name: str) -> str:
    name = Path(name).name
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def table_name_from_filename(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"[^A-Za-z0-9_]", "_", stem)


def ensure_db_dir() -> Path:
    backend_dir = Path(__file__).resolve().parents[2]
    db_dir = backend_dir / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


def save_sqlite_bytes(content: bytes, dest: Path) -> None:
    dest.write_bytes(content)


def df_to_sqlite(df: pd.DataFrame, dest: Path, table_name: str) -> None:
    conn = sqlite3.connect(str(dest))
    try:
        df.to_sql(table_name, conn, if_exists="replace", index=False)
    finally:
        conn.close()


def csv_bytes_to_sqlite(content: bytes, dest: Path, table_name: str) -> None:
    buf = io.BytesIO(content)
    df = pd.read_csv(buf)
    df_to_sqlite(df, dest, table_name)


def json_bytes_to_sqlite(content: bytes, dest: Path, table_name: str) -> None:
    buf = io.BytesIO(content)
    df = pd.read_json(buf, orient="records")
    df_to_sqlite(df, dest, table_name)


@router.get("/databases")
def list_databases() -> dict:
    """List SQLite files in backend/db for the UI database picker."""
    db_dir = ensure_db_dir()
    out: list[dict] = []
    for p in sorted(db_dir.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() in {".db", ".sqlite"}:
            st = p.stat()
            out.append({"filename": p.name, "size_bytes": st.st_size})
    return {"databases": out}


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    filename = sanitize_filename(file.filename or "uploaded")
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file extension: {ext}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    content = await file.read()
    size = len(content)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 20MB allowed.")

    db_dir = ensure_db_dir()
    stem = Path(filename).stem
    table_name = table_name_from_filename(filename)

    try:
        if ext in {".sqlite", ".db"}:
            dest_db = db_dir / filename
            save_sqlite_bytes(content, dest_db)
            final_name = dest_db.name
        elif ext == ".csv":
            dest_db = db_dir / f"{stem}.sqlite"
            csv_bytes_to_sqlite(content, dest_db, table_name)
            final_name = dest_db.name
        elif ext == ".json":
            dest_db = db_dir / f"{stem}.sqlite"
            json_bytes_to_sqlite(content, dest_db, table_name)
            final_name = dest_db.name
        else:
            raise HTTPException(status_code=415, detail="Unsupported file type")
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="Uploaded CSV/JSON appears empty or invalid") from None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion or save failed: {e}") from e

    return JSONResponse(
        status_code=201,
        content={"success": True, "filename": final_name},
    )
