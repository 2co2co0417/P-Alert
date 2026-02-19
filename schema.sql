BEGIN TRANSACTION;
CREATE TABLE IF NOT EXISTS "app_settings" (
	"id"	INTEGER,
	"pressure_threshold"	REAL NOT NULL,
	"created_at"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "condition_logs" (
	"id"	INTEGER,
	"user_id"	INTEGER NOT NULL,
	"record_date"	TEXT NOT NULL,
	"condition_score"	INTEGER NOT NULL CHECK("condition_score" IN (1, 2, 3)),
	PRIMARY KEY("id" AUTOINCREMENT),
	FOREIGN KEY("user_id") REFERENCES "users"("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "users" (
	"id"	INTEGER,
	"email"	TEXT NOT NULL UNIQUE,
	"pw_hash"	TEXT NOT NULL,
	"created_at"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
CREATE TABLE IF NOT EXISTS "weather_logs" (
	"id"	INTEGER,
	"record_date"	TEXT NOT NULL UNIQUE,
	"pressure"	REAL NOT NULL,
	"temperature"	REAL,
	"created_at"	TEXT NOT NULL,
	PRIMARY KEY("id" AUTOINCREMENT)
);
INSERT INTO "users" VALUES (1,'123@123.jp','pbkdf2:sha256:600000$JqelI4AZg9gLtUMD$69c63d4e303b2845014f31528dd3b49d417cdaa3edd4a75def658f6af335b962','2026-02-18T21:23:04');
CREATE INDEX IF NOT EXISTS "idx_condition_logs_user_id" ON "condition_logs" (
	"user_id"
);
COMMIT;
