# Snake Premium — Design Document

**Date:** 2026-06-23
**Status:** Approved

## Overview

A snake game with a premium feature: extra life on death. Free users get standard Game Over; premium users respawn at the center once per session. Real payment integration via Midtrans with GoPay.

## Project Structure

```
snake-premium/
├── server/
│   ├── index.js          # Express server + API routes
│   ├── database.js       # SQLite setup + queries
│   ├── midtrans.js       # Midtrans integration
│   └── package.json
├── public/
│   └── index.html        # Snake game + payment UI
└── README.md
```

## Backend

**Stack:** Node.js + Express + SQLite

**Dependencies:**
- `express` — web server
- `midtrans-client` — official Midtrans SDK
- `better-sqlite3` — SQLite database
- `cors` — cross-origin requests
- `uuid` — generate unique user IDs

**API Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/create-transaction` | POST | Create Midtrans payment, return redirect URL |
| `/api/notification` | POST | Midtrans webhook — updates premium status |
| `/api/check-premium/:userId` | GET | Check if user is premium |

**Payment Flow:**
1. User clicks "Get Premium" → frontend calls `/api/create-transaction`
2. Backend creates Midtrans order with GoPay, returns redirect URL
3. User redirected to Midtrans payment page → pays with GoPay
4. Midtrans sends webhook → backend updates database
5. User returns to game, premium status active

**Environment Variables (`.env`):**
```
MIDTRANS_SERVER_KEY=your_server_key
MIDTRANS_CLIENT_KEY=your_client_key
```

## Database

**SQLite Table: `users`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | TEXT (UUID) | Primary key — user identifier |
| `is_premium` | INTEGER (0/1) | Premium status |
| `order_id` | TEXT | Midtrans order ID |
| `created_at` | DATETIME | Account creation timestamp |
| `updated_at` | DATETIME | Last status update |

- First visit → UUID generated, stored in `localStorage`
- After payment → `is_premium` set to `1`
- On game load → frontend checks premium status via API

## Frontend

**UI Layout:**
- Standard snake game (same mechanics as original)
- "Get Premium — Extra Life" button below game
- Premium status indicator (⭐ Premium or Free User)

**Premium Feature — Extra Life:**
- On death: premium users → "Extra Life Used!" message, respawn at center after 1 second
- On death: free users → standard Game Over
- Extra life granted once per session only
- Snake resets to 3 segments, direction resets to right

**Visual Cues:**
- Premium users: golden border around canvas
- Extra life available: heart icon (❤️) next to score
- Extra life used: heart icon turns grey

**Payment Flow in UI:**
1. Click "Get Premium" → GoPay payment (redirect or QR)
2. After payment → page refreshes, premium badge appears
3. Premium status persists across sessions (database-backed)
