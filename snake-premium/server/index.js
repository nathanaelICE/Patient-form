require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const db = require('./database');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '../public')));

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok' });
});

// Create new user
app.post('/api/create-user', (req, res) => {
  const userId = uuidv4();
  db.createUser(userId);
  res.json({ userId });
});

// Check premium status
app.get('/api/check-premium/:userId', (req, res) => {
  const user = db.getUser(req.params.userId);
  if (!user) {
    return res.status(404).json({ error: 'User not found' });
  }
  res.json({ isPremium: Boolean(user.is_premium) });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
