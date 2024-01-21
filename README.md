# Caption Worker
A Whisper model based Youtube caption worker. It's able to follow Youtube channels, transcript captions and upload captions automatically.

## DEV

Run proxy server locally:

```
$echo "https://127.0.0.1:8000/docs to test API" ; python3 main.py
```

To connect with the DB 
```bash
$ db_file=$(cat lib/config.py | grep SQLITE_DB_FILE | awk -F'"' '{print $2}') ; sqlite3 $db_file
```

To create the table schema:
```sql
 CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    create_at INTEGER,
    auth_state TEXT,
    credentials TEXT,
    -- Transcript work credit in minutes.
    credit INTEGER,
 );

CREATE TABLE workflow (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    create_at INTEGER,
    args TEXT,
    -- 1: video_workflow
    type INTEGER,
    -- todo, locked, claimed, working, failed, done.
    status INTEGER
);

CREATE TABLE video (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_id INTEGER,
    user_id INTEGER,
    uuid TEXT,
    -- json-lized key-value pair.
    snippt TEXT,
    -- json-lized map from format to transcript id.
    transcript TEXT
);

create TABLE transcript (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT
);

CREATE TABLE payment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    create_at INTEGER,
    quantity INTEGER,
    -- pending, success, canceled, failed
    status INTEGER
)
```