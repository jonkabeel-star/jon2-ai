"use strict";

const fs = require("fs");
const path = require("path");
const { Pool } = require("pg");

async function main() {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL must be set in the backend host environment.");
  }
  const pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: process.env.PGSSL === "require" ? { rejectUnauthorized: true } : undefined,
    max: 1,
    connectionTimeoutMillis: 10000
  });
  try {
    const schemaPath = path.join(__dirname, "db", "schema.sql");
    const schema = fs.readFileSync(schemaPath, "utf8");
    await pool.query(schema);
    process.stdout.write("Jon2 AI database schema applied successfully.\n");
  } finally {
    await pool.end();
  }
}

main().catch(error => {
  process.stderr.write(`Database migration failed: ${error.message}\n`);
  process.exitCode = 1;
});
