# aunalyticsNLSQL

## Database Schema Extractor (Task 3)

This tool extracts the schema (tables, columns, types) from a database and formats it into a clean JSON structure for use with the NL-to-SQL LLM. It currently uses the Adapter Pattern with an `SQLiteExtractor`, making it easy to swap in a `PostgresExtractor` later.

### 🛠️ Usage

**Extract a local SQLite database schema to JSON:**
```bash
python3 db_tools/db_extractor.py --db path/to/db.sqlite --out schema.json
```

**Include a small number of sample rows per table for LLM context:**
```bash
python3 db_tools/db_extractor.py --db path/to/db.sqlite --samples 5 --out schema_with_samples.json
```

**Programmatic usage example:**
```python
from db_tools.db_extractor import SQLiteExtractor, format_schema_to_json

extractor = SQLiteExtractor('path/to/db.sqlite')
print(format_schema_to_json(extractor))
```

---

### 🧪 Testing

#### Automated Testing
To run the automated test suite (creates a temporary in-memory database, verifies the JSON schema logic, and cleans up):
```bash
pytest db_tools/tests/test_db_extractor.py
```
*(You should see a green `2 passed` message).*

#### Manual Testing
If you want to manually inspect the JSON output, you can generate a dummy database and run the extractor against it:

1. **Create the dummy database** (saves to `data/my_test.db`):
   ```bash
   python3 -c "from db_tools.tests.test_db_extractor import create_sample_db; create_sample_db('data/my_test.db')" 
   ```

2. **Run the extractor** (saves to `data/my_schema.json`):
   ```bash
   python3 db_tools/db_extractor.py --db data/my_test.db --out data/my_schema.json
   ```