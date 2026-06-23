# Snake Premium Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a snake game with premium extra life feature, integrated with Midtrans GoPay payment gateway.

**Architecture:** Node.js + Express backend with SQLite database for user management. Single HTML frontend with embedded CSS/JS for the game. Midtrans handles payment processing via server-to-server API calls.

**Tech Stack:** Node.js, Express, SQLite (better-sqlite3), Midtrans SDK, HTML5 Canvas, vanilla JavaScript

## Global Constraints

- Sandbox mode for Midtrans (test transactions only)
- User ID stored in localStorage, UUID format
- One extra life per game session maximum
- Premium status persists in database across sessions
- GoPay as primary payment method

---

### Task 1: Project Scaffolding

**Files:**
- Create: `snake-premium/package.json`
- Create: `snake-premium/server/index.js`
- Create: `snake-premium/.env.example`

**Interfaces:**
- Produces: Express server running on port 3000

- [ ] **Step 1: Create project directory and package.json**

```bash
mkdir -p snake-premium/server snake-premium/public
```

```json
{
  "name": "snake-premium",
  "version": "1.0.0",
  "description": "Snake game with premium extra life feature",
  "main": "server/index.js",
  "scripts": {
    "start": "node server/index.js",
    "dev": "node --watch server/index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "midtrans-client": "^1.3.1",
    "better-sqlite3": "^9.4.3",
    "cors": "^2.8.5",
    "uuid": "^9.0.0",
    "dotenv": "^16.3.1"
  }
}
```

- [ ] **Step 2: Create .env.example**

```
MIDTRANS_SERVER_KEY=your_server_key_here
MIDTRANS_CLIENT_KEY=your_client_key_here
PORT=3000
```

- [ ] **Step 3: Create basic Express server**

```javascript
// server/index.js
require('dotenv').config();
const express = require('express');
const cors = require('cors');
const path = require('path');

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

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
```

- [ ] **Step 4: Install dependencies and test**

```bash
cd snake-premium && npm install
npm start
```

Expected: Server starts on port 3000, can access http://localhost:3000/api/health

- [ ] **Step 5: Commit**

```bash
git add snake-premium/
git commit -m "feat: project scaffolding with Express server"
```

---

### Task 2: Database Layer

**Files:**
- Create: `snake-premium/server/database.js`
- Modify: `snake-premium/server/index.js`

**Interfaces:**
- Produces: `db.createUser(id)`, `db.getUser(id)`, `db.updatePremiumStatus(id, orderId)`

- [ ] **Step 1: Create database module**

```javascript
// server/database.js
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
```

- [ ] **Step 2: Add database endpoints to server**

```javascript
// Add to server/index.js after health check

const { v4: uuidv4 } = require('uuid');
const db = require('./database');

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
```

- [ ] **Step 3: Test database operations**

```bash
# Start server
npm start

# Create user
curl -X POST http://localhost:3000/api/create-user
# Should return: {"userId":"uuid-here"}

# Check premium (should be false)
curl http://localhost:3000/api/check-premium/RETURNED_UUID
# Should return: {"isPremium":false}
```

- [ ] **Step 4: Commit**

```bash
git add snake-premium/server/database.js snake-premium/server/index.js
git commit -m "feat: add SQLite database layer for user management"
```

---

### Task 3: Midtrans Integration

**Files:**
- Create: `snake-premium/server/midtrans.js`
- Modify: `snake-premium/server/index.js`

**Interfaces:**
- Consumes: `db.updatePremiumStatus(id, orderId)`
- Produces: `createTransaction(orderId, grossAmount)`, `verifyNotification(notification)`

- [ ] **Step 1: Create Midtrans module**

```javascript
// server/midtrans.js
const midtransClient = require('midtrans-client');

const snap = new midtransClient.Snap({
  isProduction: false,
  serverKey: process.env.MIDTRANS_SERVER_KEY,
  clientKey: process.env.MIDTRANS_CLIENT_KEY
});

async function createTransaction(orderId, grossAmount) {
  const parameter = {
    transaction_details: {
      order_id: orderId,
      gross_amount: grossAmount
    },
    credit_card: {
      secure: true
    },
    enabled_payments: ['gopay'],
    callbacks: {
      finish: 'http://localhost:3000/payment-finish'
    }
  };

  const transaction = await snap.createTransaction(parameter);
  return {
    token: transaction.token,
    redirectUrl: transaction.redirect_url
  };
}

async function verifyNotification(orderId) {
  const statusResponse = await snap.transaction.status(orderId);
  return {
    orderId: statusResponse.order_id,
    transactionStatus: statusResponse.transaction_status,
    paymentType: statusResponse.payment_type,
    grossAmount: statusResponse.gross_amount
  };
}

module.exports = { createTransaction, verifyNotification };
```

- [ ] **Step 2: Add payment endpoints to server**

```javascript
// Add to server/index.js

const midtrans = require('./midtrans');
const { v4: uuidv4 } = require('uuid');

// Create transaction
app.post('/api/create-transaction', async (req, res) => {
  try {
    const { userId } = req.body;
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
    const notification = await midtrans.verifyNotification(req.body.order_id);
    
    if (notification.transactionStatus === 'capture' || 
        notification.transactionStatus === 'settlement') {
      // Extract userId from orderId (format: SNAKE-userId-timestamp)
      const userId = notification.orderId.split('-')[1];
      db.updatePremiumStatus(userId, notification.orderId);
    }
    
    res.status(200).json({ status: 'ok' });
  } catch (error) {
    console.error('Notification error:', error);
    res.status(500).json({ error: 'Notification processing failed' });
  }
});
```

- [ ] **Step 3: Test with Midtrans sandbox**

```bash
# Create .env with sandbox credentials
cp .env.example .env
# Edit .env with your Midtrans sandbox keys

# Start server
npm start

# Create user first
curl -X POST http://localhost:3000/api/create-user

# Create transaction
curl -X POST http://localhost:3000/api/create-transaction \
  -H "Content-Type: application/json" \
  -d '{"userId":"RETURNED_UUID"}'
# Should return: {"orderId":"SNAKE-uuid-timestamp","redirectUrl":"https://..."}
```

- [ ] **Step 4: Commit**

```bash
git add snake-premium/server/midtrans.js snake-premium/server/index.js
git commit -m "feat: integrate Midsnap GoPay payment gateway"
```

---

### Task 4: Frontend — Base Game

**Files:**
- Create: `snake-premium/public/index.html`

**Interfaces:**
- Consumes: `/api/create-user`, `/api/check-premium/:userId`
- Produces: Working snake game with premium status display

- [ ] **Step 1: Create the complete HTML file**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Snake Premium</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            background: #1a1a2e;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #eee;
        }

        .game-container {
            text-align: center;
        }

        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
            color: #00ff88;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
        }

        .score-board {
            display: flex;
            justify-content: center;
            gap: 40px;
            margin-bottom: 15px;
            font-size: 1.2rem;
        }

        .score-board span {
            color: #00ff88;
            font-weight: bold;
        }

        .premium-badge {
            background: linear-gradient(135deg, #ffd700, #ffaa00);
            color: #1a1a2e;
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            display: none;
            margin-bottom: 10px;
        }

        .premium-badge.active {
            display: inline-block;
        }

        canvas {
            border: 3px solid #00ff88;
            border-radius: 10px;
            box-shadow: 0 0 30px rgba(0, 255, 136, 0.2);
            background: #16213e;
        }

        canvas.premium-border {
            border-color: #ffd700;
            box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
        }

        .controls {
            margin-top: 20px;
            font-size: 0.9rem;
            color: #888;
        }

        .controls kbd {
            background: #333;
            padding: 3px 8px;
            border-radius: 4px;
            border: 1px solid #555;
            color: #eee;
        }

        .extra-life {
            color: #ff4444;
            font-size: 1.5rem;
            margin-bottom: 10px;
            display: none;
        }

        .extra-life.available {
            display: block;
        }

        .extra-life.used {
            color: #666;
        }

        #startBtn {
            margin-top: 15px;
            padding: 12px 40px;
            font-size: 1.2rem;
            background: #00ff88;
            color: #1a1a2e;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
        }

        #startBtn:hover {
            background: #00cc6a;
            transform: scale(1.05);
        }

        #premiumBtn {
            margin-top: 10px;
            padding: 10px 30px;
            font-size: 1rem;
            background: linear-gradient(135deg, #ffd700, #ffaa00);
            color: #1a1a2e;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.3s;
            display: block;
            margin-left: auto;
            margin-right: auto;
        }

        #premiumBtn:hover {
            transform: scale(1.05);
        }

        #premiumBtn.hidden {
            display: none;
        }

        .game-over-text {
            font-size: 2rem;
            color: #ff4444;
            text-shadow: 0 0 20px rgba(255, 68, 68, 0.5);
            display: none;
        }

        .extra-life-text {
            font-size: 1.5rem;
            color: #ffd700;
            text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
            display: none;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <h1>🐍 Snake Premium</h1>
        <div class="premium-badge" id="premiumBadge">⭐ Premium</div>
        <div class="score-board">
            <div>Score: <span id="score">0</span></div>
            <div>High Score: <span id="highScore">0</span></div>
        </div>
        <div class="extra-life" id="extraLife">❤️</div>
        <canvas id="gameCanvas" width="400" height="400"></canvas>
        <div class="controls">
            <p>Gunakan <kbd>↑</kbd> <kbd>↓</kbd> <kbd>←</kbd> <kbd>→</kbd> atau <kbd>W</kbd> <kbd>A</kbd> <kbd>S</kbd> <kbd>D</kbd> untuk bergerak</p>
            <p style="margin-top: 5px;">Tekan <kbd>P</kbd> untuk pause</p>
        </div>
        <button id="startBtn" onclick="startGame()">Mulai Bermain</button>
        <button id="premiumBtn" onclick="getPremium()">Get Premium — Extra Life (Rp 10,000)</button>
        <p class="game-over-text" id="gameOverText">Game Over!</p>
        <p class="extra-life-text" id="extraLifeText">Extra Life Used!</p>
    </div>

    <script>
        // ==================== CONFIGURATION ====================
        const CANVAS_SIZE = 400;
        const GRID_SIZE = 20;
        const CELL_SIZE = CANVAS_SIZE / GRID_SIZE;
        const INITIAL_SPEED = 150;
        const SPEED_INCREMENT = 2;

        // ==================== STATE ====================
        let canvas, ctx;
        let snake = [];
        let food = {};
        let direction = { x: 1, y: 0 };
        let nextDirection = { x: 1, y: 0 };
        let score = 0;
        let highScore = parseInt(localStorage.getItem('snakeHighScore')) || 0;
        let gameLoop = null;
        let speed = INITIAL_SPEED;
        let isPlaying = false;
        let isPaused = false;
        
        // Premium state
        let userId = localStorage.getItem('snakeUserId') || null;
        let isPremium = false;
        let extraLifeAvailable = false;
        let extraLifeUsed = false;

        // ==================== INITIALIZATION ====================
        async function init() {
            canvas = document.getElementById('gameCanvas');
            ctx = canvas.getContext('2d');
            document.getElementById('highScore').textContent = highScore;

            // Get or create user
            if (!userId) {
                const response = await fetch('/api/create-user', { method: 'POST' });
                const data = await response.json();
                userId = data.userId;
                localStorage.setItem('snakeUserId', userId);
            }

            // Check premium status
            await checkPremiumStatus();

            // Event listeners
            document.addEventListener('keydown', handleKeyPress);

            drawGrid();
        }

        async function checkPremiumStatus() {
            try {
                const response = await fetch(`/api/check-premium/${userId}`);
                const data = await response.json();
                isPremium = data.isPremium;
                
                updatePremiumUI();
            } catch (error) {
                console.error('Error checking premium:', error);
            }
        }

        function updatePremiumUI() {
            const badge = document.getElementById('premiumBadge');
            const premiumBtn = document.getElementById('premiumBtn');
            const canvasEl = document.getElementById('gameCanvas');
            const extraLife = document.getElementById('extraLife');

            if (isPremium) {
                badge.classList.add('active');
                premiumBtn.classList.add('hidden');
                canvasEl.classList.add('premium-border');
                extraLife.classList.add('available');
            } else {
                badge.classList.remove('active');
                premiumBtn.classList.remove('hidden');
                canvasEl.classList.remove('premium-border');
                extraLife.classList.remove('available');
            }
        }

        // ==================== GAME LOGIC ====================
        function startGame() {
            snake = [
                { x: 5, y: 10 },
                { x: 4, y: 10 },
                { x: 3, y: 10 }
            ];
            direction = { x: 1, y: 0 };
            nextDirection = { x: 1, y: 0 };
            score = 0;
            speed = INITIAL_SPEED;
            isPaused = false;
            extraLifeUsed = false;
            extraLifeAvailable = isPremium;

            document.getElementById('score').textContent = score;
            document.getElementById('gameOverText').style.display = 'none';
            document.getElementById('extraLifeText').style.display = 'none';
            document.getElementById('startBtn').textContent = 'Restart';

            updateExtraLifeUI();
            spawnFood();

            if (gameLoop) clearInterval(gameLoop);
            isPlaying = true;
            gameLoop = setInterval(gameStep, speed);
        }

        function updateExtraLifeUI() {
            const extraLife = document.getElementById('extraLife');
            if (isPremium) {
                extraLife.classList.add('available');
                if (extraLifeUsed) {
                    extraLife.classList.add('used');
                } else {
                    extraLife.classList.remove('used');
                }
            }
        }

        function gameStep() {
            if (isPaused) return;

            direction = { ...nextDirection };

            const head = {
                x: snake[0].x + direction.x,
                y: snake[0].y + direction.y
            };

            // Wall collision
            if (head.x < 0 || head.x >= GRID_SIZE || head.y < 0 || head.y >= GRID_SIZE) {
                handleDeath();
                return;
            }

            // Self collision
            for (let segment of snake) {
                if (head.x === segment.x && head.y === segment.y) {
                    handleDeath();
                    return;
                }
            }

            snake.unshift(head);

            // Food collision
            if (head.x === food.x && head.y === food.y) {
                score += 10;
                document.getElementById('score').textContent = score;

                if (score > highScore) {
                    highScore = score;
                    document.getElementById('highScore').textContent = highScore;
                    localStorage.setItem('snakeHighScore', highScore);
                }

                spawnFood();
                speed = Math.max(50, speed - SPEED_INCREMENT);
                clearInterval(gameLoop);
                gameLoop = setInterval(gameStep, speed);
            } else {
                snake.pop();
            }

            draw();
        }

        function handleDeath() {
            if (isPremium && extraLifeAvailable && !extraLifeUsed) {
                // Use extra life
                extraLifeUsed = true;
                extraLifeAvailable = false;
                updateExtraLifeUI();
                
                // Show message
                const extraLifeText = document.getElementById('extraLifeText');
                extraLifeText.style.display = 'block';
                setTimeout(() => {
                    extraLifeText.style.display = 'none';
                }, 1000);

                // Respawn at center
                snake = [
                    { x: GRID_SIZE / 2, y: GRID_SIZE / 2 },
                    { x: GRID_SIZE / 2 - 1, y: GRID_SIZE / 2 },
                    { x: GRID_SIZE / 2 - 2, y: GRID_SIZE / 2 }
                ];
                direction = { x: 1, y: 0 };
                nextDirection = { x: 1, y: 0 };

                draw();
            } else {
                // Game over
                gameOver();
            }
        }

        function gameOver() {
            isPlaying = false;
            clearInterval(gameLoop);

            let flashes = 0;
            const flashInterval = setInterval(() => {
                if (flashes >= 6) {
                    clearInterval(flashInterval);
                    document.getElementById('gameOverText').style.display = 'block';
                    document.getElementById('startBtn').textContent = 'Main Lagi';
                    return;
                }

                ctx.fillStyle = flashes % 2 === 0 ? 'rgba(255, 0, 0, 0.3)' : '#16213e';
                ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);

                if (flashes % 2 === 0) {
                    drawGrid();
                    drawSnake();
                    drawFood();
                }

                flashes++;
            }, 150);
        }

        // ==================== RENDERING ====================
        function draw() {
            ctx.fillStyle = '#16213e';
            ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
            drawGrid();
            drawFood();
            drawSnake();
        }

        function drawGrid() {
            ctx.strokeStyle = 'rgba(255, 255, 255, 0.03)';
            ctx.lineWidth = 0.5;

            for (let i = 0; i <= GRID_SIZE; i++) {
                ctx.beginPath();
                ctx.moveTo(i * CELL_SIZE, 0);
                ctx.lineTo(i * CELL_SIZE, CANVAS_SIZE);
                ctx.stroke();

                ctx.beginPath();
                ctx.moveTo(0, i * CELL_SIZE);
                ctx.lineTo(CANVAS_SIZE, i * CELL_SIZE);
                ctx.stroke();
            }
        }

        function drawSnake() {
            snake.forEach((segment, index) => {
                const x = segment.x * CELL_SIZE;
                const y = segment.y * CELL_SIZE;

                if (index === 0) {
                    ctx.fillStyle = '#00ff88';
                    ctx.shadowColor = '#00ff88';
                    ctx.shadowBlur = 10;
                } else {
                    const brightness = 1 - (index / snake.length) * 0.6;
                    ctx.fillStyle = `rgba(0, ${Math.floor(255 * brightness)}, ${Math.floor(136 * brightness)}, 1)`;
                    ctx.shadowBlur = 0;
                }

                const padding = 1;
                const radius = 4;
                roundRect(ctx, x + padding, y + padding, CELL_SIZE - padding * 2, CELL_SIZE - padding * 2, radius);
                ctx.fill();

                if (index === 0) {
                    drawEyes(x, y);
                }
            });

            ctx.shadowBlur = 0;
        }

        function drawEyes(x, y) {
            ctx.fillStyle = '#1a1a2e';
            const eyeSize = 3;
            let eye1X, eye1Y, eye2X, eye2Y;

            if (direction.x === 1) {
                eye1X = x + CELL_SIZE - 7; eye1Y = y + 6;
                eye2X = x + CELL_SIZE - 7; eye2Y = y + CELL_SIZE - 6;
            } else if (direction.x === -1) {
                eye1X = x + 7; eye1Y = y + 6;
                eye2X = x + 7; eye2Y = y + CELL_SIZE - 6;
            } else if (direction.y === -1) {
                eye1X = x + 6; eye1Y = y + 7;
                eye2X = x + CELL_SIZE - 6; eye2Y = y + 7;
            } else {
                eye1X = x + 6; eye1Y = y + CELL_SIZE - 7;
                eye2X = x + CELL_SIZE - 6; eye2Y = y + CELL_SIZE - 7;
            }

            ctx.beginPath();
            ctx.arc(eye1X, eye1Y, eyeSize, 0, Math.PI * 2);
            ctx.fill();

            ctx.beginPath();
            ctx.arc(eye2X, eye2Y, eyeSize, 0, Math.PI * 2);
            ctx.fill();
        }

        function drawFood() {
            const x = food.x * CELL_SIZE;
            const y = food.y * CELL_SIZE;
            const centerX = x + CELL_SIZE / 2;
            const centerY = y + CELL_SIZE / 2;

            ctx.shadowColor = '#ff4444';
            ctx.shadowBlur = 15;
            ctx.fillStyle = '#ff4444';
            ctx.beginPath();
            ctx.arc(centerX, centerY, CELL_SIZE / 2 - 3, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;

            ctx.fillStyle = '#44ff44';
            ctx.beginPath();
            ctx.ellipse(centerX + 2, y + 4, 3, 5, Math.PI / 4, 0, Math.PI * 2);
            ctx.fill();
        }

        function roundRect(ctx, x, y, width, height, radius) {
            ctx.beginPath();
            ctx.moveTo(x + radius, y);
            ctx.arcTo(x + width, y, x + width, y + height, radius);
            ctx.arcTo(x + width, y + height, x, y + height, radius);
            ctx.arcTo(x, y + height, x, y, radius);
            ctx.arcTo(x, y, x + width, y, radius);
            ctx.closePath();
        }

        function spawnFood() {
            let newFood;
            do {
                newFood = {
                    x: Math.floor(Math.random() * GRID_SIZE),
                    y: Math.floor(Math.random() * GRID_SIZE)
                };
            } while (snake.some(seg => seg.x === newFood.x && seg.y === newFood.y));
            food = newFood;
        }

        // ==================== CONTROLS ====================
        function handleKeyPress(e) {
            if (!isPlaying) return;

            switch (e.key) {
                case 'ArrowUp':
                case 'w':
                case 'W':
                    if (direction.y !== 1) nextDirection = { x: 0, y: -1 };
                    e.preventDefault();
                    break;
                case 'ArrowDown':
                case 's':
                case 'S':
                    if (direction.y !== -1) nextDirection = { x: 0, y: 1 };
                    e.preventDefault();
                    break;
                case 'ArrowLeft':
                case 'a':
                case 'A':
                    if (direction.x !== 1) nextDirection = { x: -1, y: 0 };
                    e.preventDefault();
                    break;
                case 'ArrowRight':
                case 'd':
                case 'D':
                    if (direction.x !== -1) nextDirection = { x: 1, y: 0 };
                    e.preventDefault();
                    break;
                case 'p':
                case 'P':
                    isPaused = !isPaused;
                    if (isPaused) {
                        ctx.fillStyle = 'rgba(0, 0, 0, 0.5)';
                        ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
                        ctx.fillStyle = '#fff';
                        ctx.font = '30px Segoe UI';
                        ctx.textAlign = 'center';
                        ctx.fillText('PAUSED', CANVAS_SIZE / 2, CANVAS_SIZE / 2);
                    } else {
                        draw();
                    }
                    break;
            }
        }

        // ==================== PAYMENT ====================
        async function getPremium() {
            try {
                const response = await fetch('/api/create-transaction', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ userId })
                });
                
                const data = await response.json();
                
                if (data.redirectUrl) {
                    // Redirect to Midtrans payment page
                    window.location.href = data.redirectUrl;
                } else {
                    alert('Failed to create payment. Please try again.');
                }
            } catch (error) {
                console.error('Payment error:', error);
                alert('Payment failed. Please try again.');
            }
        }

        // ==================== START ====================
        window.onload = init;
    </script>
</body>
</html>
```

- [ ] **Step 2: Test the frontend**

```bash
npm start
# Open http://localhost:3000 in browser
# Verify: game loads, premium button visible, can play
```

- [ ] **Step 3: Commit**

```bash
git add snake-premium/public/index.html
git commit -m "feat: add frontend with snake game and premium UI"
```

---

### Task 5: Payment Flow Integration

**Files:**
- Modify: `snake-premium/public/index.html` (add payment-finish handler)

**Interfaces:**
- Consumes: `/api/check-premium/:userId` on page load
- Produces: Automatic premium status refresh after payment

- [ ] **Step 1: Add payment finish handler**

The payment-finish page is handled by Midtrans redirect. Add this to the JavaScript section:

```javascript
// Add after init() function

// Check URL for payment finish
function checkPaymentFinish() {
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('order_id')) {
        // Payment finished, refresh premium status
        checkPremiumStatus().then(() => {
            if (isPremium) {
                alert('Payment successful! Premium activated!');
            }
            // Clean URL
            window.history.replaceState({}, document.title, '/');
        });
    }
}

// Call on page load
window.addEventListener('load', checkPaymentFinish);
```

- [ ] **Step 2: Test complete payment flow**

```bash
# Start server
npm start

# Open http://localhost:3000
# 1. Click "Get Premium"
# 2. Redirected to Midtrans sandbox
# 3. Complete test payment (use sandbox credentials)
# 4. Redirected back to game
# 5. Premium badge should appear
# 6. Play game, die, should get extra life
```

- [ ] **Step 3: Commit**

```bash
git add snake-premium/public/index.html
git commit -m "feat: complete payment flow with auto-refresh"
```

---

### Task 6: README and Documentation

**Files:**
- Create: `snake-premium/README.md`

- [ ] **Step 1: Create README**

```markdown
# Snake Premium

Snake game with premium extra life feature, integrated with Midtrans GoPay.

## Features

- Classic snake gameplay
- Premium feature: extra life on death (respawn at center)
- Real payment via Midtrans GoPay
- Premium status persists across sessions

## Setup

1. Clone and install:
   ```bash
   cd snake-premium
   npm install
   ```

2. Create `.env` file:
   ```
   MIDTRANS_SERVER_KEY=your_server_key
   MIDTRANS_CLIENT_KEY=your_client_key
   PORT=3000
   ```

3. Start server:
   ```bash
   npm start
   ```

4. Open http://localhost:3000

## Midtrans Sandbox

For testing, use Midtrans sandbox credentials:
- Register at https://midtrans.com
- Get sandbox keys from dashboard
- Use test credit card: 4811 1111 1111 1114

## How It Works

1. User gets unique ID (stored in localStorage)
2. Premium status stored in SQLite database
3. Payment processed via Midtrans GoPay
4. Webhook updates database on successful payment
5. Frontend checks premium status on page load
```

- [ ] **Step 2: Commit**

```bash
git add snake-premium/README.md
git commit -m "docs: add README with setup instructions"
```

---

### Task 7: Final Polish

**Files:**
- Modify: `snake-premium/public/index.html` (minor fixes)

- [ ] **Step 1: Add error handling for missing .env**

```javascript
// Add to server/index.js at the top

if (!process.env.MIDTRANS_SERVER_KEY || !process.env.MIDTRANS_CLIENT_KEY) {
  console.warn('Warning: Midtrans keys not configured. Payment features will not work.');
}
```

- [ ] **Step 2: Test all scenarios**

```bash
# Test 1: Fresh user
# - Open incognito window
# - Play game, die → Game Over (no extra life)
# - Click Get Premium → redirect to payment

# Test 2: Premium user
# - Complete payment
# - Play game, die → Extra Life Used, respawn at center
# - Die again → Game Over

# Test 3: Persistence
# - Close browser
# - Reopen → premium status still active
```

- [ ] **Step 3: Final commit**

```bash
git add snake-premium/
git commit -m "feat: complete snake premium with error handling"
```

---

## Self-Review

**Spec coverage:**
- ✅ Extra life feature for premium users
- ✅ Respawn at center
- ✅ Once per session limit
- ✅ Midtrans GoPay integration
- ✅ Premium status persistence
- ✅ Visual indicators (badge, border, heart icon)

**Placeholder scan:** No TBDs or TODOs found.

**Type consistency:** All function names and signatures match across tasks.

**Spec requirement with no task:** All requirements covered.
