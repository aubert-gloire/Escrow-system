# Crypto Escrow Bot - Telegram Integration

A secure, automated escrow system for cryptocurrency transactions via Telegram, supporting BTC, USDT (ERC20/TRC20), ETH, and LTC.

## Features

- **Multi-currency support**: BTC, USDT, ETH, LTC
- **Automated payment processing** via NOWPayments/Coinbase Commerce
- **Secure escrow workflow** with dispute resolution
- **Webhook-based confirmations** with HMAC verification
- **Admin panel** for manual interventions
- **Comprehensive logging** and monitoring

## Architecture

```
Buyer -> /escrow -> Bot creates invoice -> Payment -> Webhook confirms -> 
Funds in escrow -> Seller delivers -> Buyer confirms -> Release funds
```

## Tech Stack

- **Bot Framework**: aiogram (Python)
- **Payment Gateway**: NOWPayments
- **Database**: PostgreSQL
- **Hosting**: VPS with HTTPS
- **Automation**: n8n/Make integration
- **Backup Notifications**: Signal CLI

## Quick Start

1. Clone and install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Initialize database:
```bash
python scripts/init_db.py
```

4. Run the bot:
```bash
python main.py
```

## Project Structure

```
├── bot/                    # Bot logic and handlers
├── database/              # Database models and migrations
├── payments/              # Payment gateway integrations
├── webhooks/              # Webhook handlers
├── admin/                 # Admin panel and commands
├── config/                # Configuration files
├── scripts/               # Utility scripts
└── tests/                 # Test suites
```

## Development Timeline

- **Week 1**: Setup & skeleton ✅
- **Week 2**: Payments & webhooks
- **Week 3**: Bot UX & admin flow
- **Week 4**: Testing & launch

## Legal Notice

This software is provided for educational purposes. Users must comply with local regulations regarding money services and cryptocurrency handling.
