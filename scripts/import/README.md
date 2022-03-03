# Importing documents

__Warning__: Using this script will drop collections before importing new documents.

## How to
1. Create a .JSON-file for each collection with the name of the collection as the file name (in the same folder as the import.sh file).
2. Put your documents in the JSON-files (JSON-file = array of document-objects). For example a `clients.json`:
```
[
  {
    "title": "test-client-1",
    "is_active": true,
    "phone_number": "123456",
    "api_id": 123456,
    "api_hash": "123456",
    "session_hash": "123456"
  }
]
```

3. Adjust the variables at the beginning of `import.sh`
4. `chmod +x ./scripts/import/import.sh` to make `import.sh` executeable
5. Run `./scripts/import/import.sh`

The JSON-files are ignored by Git.