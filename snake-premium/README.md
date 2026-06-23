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
