BEGIN TRANSACTION;
CREATE TABLE visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ip TEXT,
                    x_forwarded_for TEXT,
                    user_agent TEXT,
                    host TEXT,
                    path TEXT,
                    query_string TEXT,
                    target_url TEXT
                );
INSERT INTO "visits" VALUES(1,'2025-12-02T19:01:50.549449Z','127.0.0.1','','Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 YaBrowser/25.10.0.0 Safari/537.36','127.0.0.1:8080','/','','https://example.com/');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('visits',1);
COMMIT;
