# 🔒 Escrow Bot Phase 1

**A secure, automated escrow system for cryptocurrency transactions via Telegram**

## Phase 1 Features

✅ Multi-currency support (BTC, USDT, LTC)
✅ Telegram group creation with bot as admin
✅ Seller/Buyer registration with wallet addresses  
✅ Escrow deal creation
✅ Manual deposit tracking
✅ Deal completion workflow
✅ Basic dispute handling
✅ Admin verification commands
✅ User reputation tracking

## Tech Stack

- **Bot**: aiogram 3.4.1 (Python async)
- **Database**: MongoDB Atlas (free tier)
- **Backend**: FastAPI + Uvicorn
- **Hosting**: Render (Starter plan recommended for 24/7 uptime)
- **Payment Model**: Manual escrow deposits

## Project Structure

```
phase1_bot/
├── bot/
│   ├── handlers/        # Command and callback handlers
│   ├── keyboards/       # Inline/Reply keyboards
│   ├── utils/          # Validators, formatters, group manager
│   └── main.py         # Bot entry point
├── database/
│   ├── mongo.py        # MongoDB connection
│   ├── models.py       # Document schemas
│   └── crud.py         # Database operations
├── backend/
│   ├── app.py          # FastAPI application
│   └── routes/         # API endpoints
├── config/
│   └── settings.py     # Configuration from env vars
├── requirements.txt
├── Procfile
├── render.yaml
├── .env.example
└── README.md
```

## Quick Start (Local Development)

### 1. Setup MongoDB Atlas
```bash
# Create free account at mongodb.com/cloud/atlas
# Create M0 cluster and get connection string
# Create database user and note password
```

### 2. Clone and Install
```bash
cd phase1_bot
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env

# Edit .env with:
# - Your Telegram bot token
# - MongoDB connection URI
# - Your escrow wallet addresses (BTC, USDT, LTC)
# - Your admin Telegram ID
```

### 4. Run Locally
```bash
# In terminal 1: Run bot
python bot/main.py

# In terminal 2: Run backend
python -m uvicorn backend.app:app --reload
```

## Deployment on Render

### 1. Prepare Repository
```bash
git init
git add .
git commit -m "Phase 1 implementation"
git push origin main
```

### 2. Create Render Services
- Go to [render.com](https://render.com)
- Create new Web Service (escrow-api)
- Create new Background Worker (escrow-bot)
- Connect your GitHub repo
- Add environment variables

### 3. Environment Variables on Render
```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_SESSION_STRING=your_telethon_session_string
MONGO_URI=mongodb+srv://user:pass@cluster.mongodb.net/escrow_phase1
MONGO_DB_NAME=escrow_phase1
ADMIN_USER_IDS=your_numeric_telegram_id
ESCROW_BTC_ADDRESS=your_btc_address
ESCROW_USDT_ADDRESS=your_usdt_address
ESCROW_ETH_ADDRESS=your_eth_address
ESCROW_LTC_ADDRESS=your_ltc_address
SECRET_KEY=generate_a_long_random_secret
SUPPORTED_CURRENCIES=["BTC","USDT","ETH","LTC"]
PYTHONUNBUFFERED=1
LOG_LEVEL=INFO
HEARTBEAT_INTERVAL_SECONDS=300
```

### 4. Deploy
- Push to GitHub
- Render auto-deploys both services

### 5. Keep It 24/7 On Render
- Use `Starter` (or higher) plan for both web and worker services.
- Free services can sleep or be resource-constrained, which causes cold starts and lag.
- Keep web health check on `/ready` and monitor restart events in Render logs.
- The bot logs a heartbeat every `HEARTBEAT_INTERVAL_SECONDS` seconds and attempts MongoDB reconnection if the database drops.

## Bot Commands

### User Commands
- `/start` - Start bot and show menu
- `/seller` - Register as seller (asks for preferred currency and address)
- `/buyer` - Register as buyer
- `/escrow` - Create new escrow deal
- `/mydeals` - View your active deals
- `/help` - Show help message

### Deal Commands
- `/confirm_deposit {tx_hash}` - Submit transaction hash as buyer
- `/delivered` - Mark deal as delivered (seller)
- `/complete_deal` - Confirm receipt and complete deal (buyer)
- `/dispute` - Raise dispute if issues (buyer)

### Admin Commands
- `/admin` - Show admin panel (admin only)
- `/verify_deposit {deal_id} {confirmations}` - Verify deposit
- `/resolve_dispute {deal_id} {winner}` - Resolve dispute

## Workflow

### 1. Role Selection
```
User starts bot
↓
/seller or /buyer
↓
Seller: Select currency → Enter address
Buyer: Ready to create deals
```

### 2. Deal Creation
```
/escrow
↓
Enter amount
↓
Enter description
↓
Bot creates group + generates unique deal ID
↓
Bot displays escrow address
```

### 3. Payment (Manual Phase 1)
```
Bot: "Send X to escrow address"
↓
Buyer makes payment on blockchain
↓
/confirm_deposit {tx_hash}
↓
Admin: /verify_deposit {deal_id}
↓
Status updates to DEPOSITED
```

### 4. Delivery & Completion
```
Seller: /delivered (when goods delivered)
↓
Buyer receives notification
↓
Buyer: /complete_deal (confirms receipt)
↓
Deal completed, reputation updated
```

### 5. Dispute (If needed)
```
Buyer: /dispute (if issues)
↓
Admin: /resolve_dispute {deal_id} {buyer|seller}
↓
Funds distributed based on decision
```

## Database Schema (MongoDB)

### Users Collection
```javascript
{
  _id: 123456789,           // Telegram user ID
  username: "john_doe",
  first_name: "John",
  role: "buyer",            // or "seller"
  seller_addresses: {
    BTC: "1A1z7agoat91...",
    USDT: "0x742d...",
    LTC: "Ltk3s..."
  },
  stats: {
    completed_deals: 5,
    disputes_won: 1,
    ...
  }
}
```

### Deals Collection
```javascript
{
  deal_id: "DEAL_ABC123",
  buyer_id: 123456789,
  seller_id: 987654321,
  amount: 0.5,
  currency: "BTC",
  escrow_address: "1A1z7agoat91...",
  deposit_tx_hash: "abc123def456...",
  deposit_confirmed: true,
  status: "COMPLETED",
  group_id: -1001234567890,
  group_link: "https://t.me/...",
  ...
}
```

## API Endpoints

### Deals
- `POST /api/deals/create` - Create deal
- `GET /api/deals/{deal_id}` - Get deal details
- `GET /api/deals/user/{user_id}` - Get user's deals

### Admin
- `POST /api/admin/verify-deposit/{deal_id}` - Verify deposit
- `POST /api/admin/resolve-dispute/{deal_id}` - Resolve dispute

## Error Handling

| Error | Handling |
|-------|----------|
| MongoDB offline | Retry with exponential backoff |
| Invalid address | Re-ask with format help |
| Bot not admin | Notify user, ask to manually add |
| Group creation fails | Continue with deal anyway |
| Expired deal | Auto-cancel, notify both parties |

## Testing

```bash
# Run tests
pytest tests/

# Test bot locally
python bot/main.py

# Test API
python -m uvicorn backend.app:app --reload
curl http://localhost:8000/health
```

## Phase 2 Roadmap

🔜 Blockchain listener for auto-verification
🔜 Smart contract integration
🔜 Multi-signature wallets
🔜 Automated fund release
🔜 Advanced dispute resolution
🔜 Reputation scoring system
🔜 KYC verification

## Security Considerations

⚠️ **Phase 1 Limitations**:
- Manual deposit verification (prone to errors)
- No blockchain integration (can't auto-verify)
- Admin dependency (centralized)
- Limited escrow security

✅ **Phase 1 Protections**:
- Crypto address validation
- Transaction hash recording
- Audit trail in MongoDB
- Deal expiry (24h for deposit)
- Admin verification flow

## Support

For issues or questions:
1. Check `/help` in bot
2. Contact admin: @your_username
3. Reference deal ID when reporting issues

## License

Proprietary - All rights reserved

---

**Built with ❤️ for secure cryptocurrency transactions**
