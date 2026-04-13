import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_db_path = os.getenv("DB_PATH")
DB = _db_path if _db_path else os.path.join(BASE_DIR, "db.sqlite")
