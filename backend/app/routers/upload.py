from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import sqlite3
import pandas as pd
import io
import re

router = APIRouter()


MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXTENSIONS = {".sqlite", ".csv", ".json"}


def sanitize_filename(name: str) -> str:
    name = Path(name).name
    # keep alphanum, dash, underscore, dot
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


def table_name_from_filename(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"[^A-Za-z0-9_]", "_", stem)


def ensure_db_dir() -> Path:
    # backend/db relative to this file: routers -> app -> backend
    backend_dir = Path(__file__).resolve().parents[2]
    db_dir = backend_dir / "db"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


def save_sqlite_bytes(content: bytes, dest: Path) -> None:
    with open(dest, "wb") as f:
        f.write(content)


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
    # Expecting a flat array of objects
    df = pd.read_json(buf, orient="records")
    df_to_sqlite(df, dest, table_name)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = sanitize_filename(file.filename or "uploaded")
    ext = Path(filename).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file extension: {ext}")

    content = await file.read()
    size = len(content)
    if size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 20MB allowed.")

    db_dir = ensure_db_dir()

    stem = Path(filename).stem
    table_name = table_name_from_filename(filename)
    dest_db = db_dir / f"{stem}.sqlite"

    try:
        if ext == ".sqlite":
            # Save directly
            save_sqlite_bytes(content, dest_db)
        elif ext == ".csv":
            csv_bytes_to_sqlite(content, dest_db, table_name)
        elif ext == ".json":
            json_bytes_to_sqlite(content, dest_db, table_name)
        else:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    except pd.errors.EmptyDataError:
        raise HTTPException(status_code=400, detail="Uploaded CSV/JSON appears empty or invalid")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid data: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversion or save failed: {e}")

    return JSONResponse(status_code=201, content={"success": True, "filename": dest_db.name})
