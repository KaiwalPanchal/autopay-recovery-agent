"""Reset the local SQLite database from the paise-denominated authentic customer persona seed."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import db
if __name__ == '__main__':
    customers = db.reset_to_seed()
    print(f'Seeded {len(customers)} authentic customer personas (no placeholder phone numbers).')
