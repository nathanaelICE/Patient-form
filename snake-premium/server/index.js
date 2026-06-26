require('dotenv').config();
const express = require('express');

if (!process.env.MIDTRANS_SERVER_KEY || !process.env.MIDTRANS_CLIENT_KEY) {
  console.warn('Warning: Midtrans keys not configured. Payment features will not work.');
}
const cors = require('cors');
const path = require('path');
const { v4: uuidv4 } = require('uuid');
const db = require('./database');
const midtrans = require('./midtrans');

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

// Create transaction
app.post('/api/create-transaction', async (req, res) => {
  try {
    const { userId } = req.body;
    if (!userId) {
      return res.status(400).json({ error: 'userId is required' });
    }
    const orderId = `SNAKE-${userId}-${Date.now()}`;
    const amount = 10000; // Rp 10,000

    const { redirectUrl } = await midtrans.createTransaction(orderId, amount);

    res.json({ orderId, redirectUrl });
  } catch (error) {
    console.error('Transaction error:', error);
    res.status(500).json({ error: 'Failed to create transaction' });
  }
});

// Midtrans notification webhook
app.post('/api/notification', async (req, res) => {
  try {
    if (!req.body.order_id) {
      return res.status(400).json({ error: 'order_id is required' });
    }
    const notification = await midtrans.verifyNotification(req.body.order_id);

    if (notification.transactionStatus === 'capture' ||
        notification.transactionStatus === 'settlement') {
      // Extract userId from orderId (format: SNAKE-{uuid}-{timestamp})
      const userId = notification.orderId.replace(/^SNAKE-/, '').replace(/-\d+$/, '');
      db.updatePremiumStatus(userId, notification.orderId);
    }

    res.status(200).json({ status: 'ok' });
  } catch (error) {
    console.error('Notification error:', error);
    res.status(500).json({ error: 'Notification processing failed' });
  }
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
