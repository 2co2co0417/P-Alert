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
	"condition_score"	INTEGER NOT NULL CHECK("condition_score" BETWEEN 1 AND 5),
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

CREATE INDEX IF NOT EXISTS "idx_condition_logs_user_id" ON "condition_logs" (
	"user_id"
);
COMMIT;
