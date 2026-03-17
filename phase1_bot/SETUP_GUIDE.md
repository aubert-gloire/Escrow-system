# Phase 1 Setup Guide

## ✅ What You Already Have

Configure these values in your own environment:

| Item | Value | Status |
|------|-------|--------|
| Telegram Bot Token | `your_bot_token_here` | Required |
| Admin Telegram ID | `your_numeric_telegram_id` | Required |
| Secret Key | `generate_a_long_random_secret` | Required |
| NOWPayments API | Optional (Phase 2+) | Optional |

Use placeholder values in `.env.example` and store real values only in `.env` and Render env vars.

---

## 📋 What You STILL NEED TO ADD

### 1. **MongoDB Atlas Connection** (REQUIRED)

**Why**: Phase 1 uses MongoDB instead of PostgreSQL for simplicity

**Steps**:

1. Go to [mongodb.com/cloud/atlas](https://mongodb.com/cloud/atlas)
2. Create a FREE account
3. Create a FREE M0 cluster
4. Click "Connect" → "Connect your application"
5. Copy the connection string that looks like:

   ```
   mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/escrow_phase1?retryWrites=true&w=majority
   ```

6. Replace `username`, `password`, and `cluster0` with your actual values
7. Add to `.env`:

   ```
   MONGO_URI=mongodb+srv://your_username:your_password@your_cluster.mongodb.net/escrow_phase1?retryWrites=true&w=majority
   ```

**Tips**:

- Keep username/password simple (no special chars like @, $, etc. - use MongoDB's URL encoding if needed)
- Database name is already `escrow_phase1` in the connection string
- M0 (free tier) is enough for Phase 1 testing

---

### 2. **Cryptocurrency Escrow Addresses** (REQUIRED for Phase 1 to work)

**What are these**: Wallet addresses where buyers will send cryptocurrency

**You need ONE of these** (or all three if you want full currency support):

#### Option A: Just BTC (Simplest)

```env
ESCROW_BTC_ADDRESS=your_bitcoin_address_here
ESCROW_USDT_ADDRESS=
ESCROW_LTC_ADDRESS=
```

#### Option B: All Three (Full Support)

```env
ESCROW_BTC_ADDRESS=1A1z7agoat91aXTv7LCJ...
ESCROW_USDT_ADDRESS=0x742d35Cc6634C0532925a3b844Bc833e...
ESCROW_LTC_ADDRESS=Ltk3sRbWk2k6eHmCf1D85y7V7KZGTUvJWW
```

**How to get these addresses**:

- **BTC**: Use any Bitcoin wallet (Coinbase, Kraken, Trust Wallet, etc.)
- **USDT**: Use any Ethereum wallet (same address format as required)
- **LTC**: Use any Litecoin wallet

---

## 🚀 Quick Start

### Step 1: Clone .env.example

```bash
cd phase1_bot
cp .env.example .env
```

### Step 2: Edit .env

Add only these two things:

```env
# Add your MongoDB connection URI
MONGO_URI=mongodb+srv://...

# Add your escrow addresses (at least one)
ESCROW_BTC_ADDRESS=1A1z7agoat91...
```

Keep everything else as-is!

### Step 3: Install & Run

```bash
# Install dependencies
pip install -r requirements.txt

# Terminal 1: Run bot
python bot/main.py

# Terminal 2: Run backend
python -m uvicorn backend.app:app --reload
```

### Step 4: Test the Bot

- Open Telegram and search for your bot
- Click `/start`
- Try `/seller` or `/buyer`
- Try `/escrow` to create a deal

---

## 🌍 Deploy to Render

### Step 1: Push to GitHub

```bash
git add .
git commit -m "Phase 1: Ready for deployment"
git push origin main
```

### Step 2: Create Render Services

**Service 1: Web (Backend API)**

- Type: Web Service
- Name: `escrow-api`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m uvicorn backend.app:app --host 0.0.0.0 --port $PORT`

**Service 2: Background Worker (Bot)**

- Type: Background Worker
- Name: `escrow-bot`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python bot/main.py`

### Step 3: Add Environment Variables (in Render Dashboard)

```
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=your_numeric_telegram_id
SECRET_KEY=generate_a_long_random_secret
MONGO_URI=mongodb+srv://...
ESCROW_BTC_ADDRESS=...
ESCROW_USDT_ADDRESS=...
ESCROW_LTC_ADDRESS=...
```

### Step 4: Deploy

- Click "Deploy"
- Both services start automatically
- Your bot is now LIVE! 🚀

---

## ✅ Verification Checklist

After setup, verify:

- [ ] `.env` file created with all required values
- [ ] MongoDB Atlas cluster created and connected
- [ ] At least one escrow address added
- [ ] Bot runs locally: `python bot/main.py`
- [ ] Backend runs locally: `python -m uvicorn backend.app:app --reload`
- [ ] Bot responds to `/start` command
- [ ] Can register with `/seller` and `/buyer`
- [ ] Can create deal with `/escrow`

---

## 🔒 Security Notes

**IMPORTANT**:

- Never commit real `.env` file to GitHub (it's in `.gitignore`)
- Only commit `.env.example` with placeholder values
- Your credentials are safe on Render (they use encryption)
- Add IP whitelist to MongoDB Atlas if needed

---

## 🆘 Troubleshooting

### Bot doesn't respond?

- Check `TELEGRAM_BOT_TOKEN` is correct
- Check bot is running: `python bot/main.py`
- Check logs: `logs/escrow_bot.log`

### MongoDB connection fails?

- Verify `MONGO_URI` doesn't have typos
- Check MongoDB cluster is created
- Verify username/password is correct
- Check IP whitelist in MongoDB Atlas (should allow 0.0.0.0)

### Render deployment fails?

- Check `requirements.txt` is complete
- Check log files in Render dashboard
- Verify all env vars are set
- Try redeploying manual

---

## 📚 Next Steps

1. **Test locally** with Phase 1 workflow
2. **Deploy to Render** when ready
3. **Phase 2**: Add blockchain auto-verification
4. **Phase 3**: Add smart contracts

---

**That's it! Phase 1 is now ready to deploy! 🎉**
