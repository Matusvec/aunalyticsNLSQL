import os
from fastapi import APIRouter

# Create the router instance
router = APIRouter()

@router.get("/api/databases")
def get_databases():
    """
    Scans the backend/db/ folder and returns a list of .sqlite filenames.
    """
    # The path relative to where the server starts
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(base_dir, "db") 
    
    try:
        # 1. List all files in the directory
        # 2. Filter: Only keep files that end with '.sqlite'
        # 3. Return them as a clean list
        files = [f for f in os.listdir(db_path) if f.endswith('.sqlite')]
        
        return {"databases": files}
        
    except FileNotFoundError:
        # Usability: If the folder is missing, don't crash, just tell us why
        return {"error": f"Directory {db_path} not found.", "databases": []}