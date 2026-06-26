const Database = require('better-sqlite3');
const path = require('path');

const db = new Database(path.join(__dirname, 'snake.db'));

// Create table
db.exec(`
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    is_premium INTEGER DEFAULT 0,
    order_id TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
  )
`);

function createUser(id) {
  const stmt = db.prepare('INSERT OR IGNORE INTO users (id) VALUES (?)');
  return stmt.run(id);
}

function getUser(id) {
  return db.prepare('SELECT * FROM users WHERE id = ?').get(id);
}

function updatePremiumStatus(id, orderId) {
  const stmt = db.prepare(`
    UPDATE users
    SET is_premium = 1, order_id = ?, updated_at = CURRENT_TIMESTAMP
    WHERE id = ?
  `);
  return stmt.run(orderId, id);
}

module.exports = { createUser, getUser, updatePremiumStatus };
