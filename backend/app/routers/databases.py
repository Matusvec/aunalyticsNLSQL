import os
from fastapi import APIRouter

router = APIRouter()

@router.get("/databases") # No '/api' here! main.py handles that.
async def list_databases():
    # Looks for 'backend/db' starting from the root of the project
    db_path = os.path.join(os.getcwd(), "backend", "db")
    
    try:
        files = [f for f in os.listdir(db_path) if f.endswith(".sqlite") or f.endswith(".db")]
        return {"databases": files}
    except Exception as e:
        return {"error": str(e), "databases": []}

