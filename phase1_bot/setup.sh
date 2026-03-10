#!/bin/bash
# Phase 1 Quick Setup Script

echo "🔒 Escrow Bot Phase 1 - Setup Guide"
echo "===================================="
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📋 Creating .env from .env.example..."
    cp .env.example .env
    echo "✅ .env created"
    echo ""
    echo "⚠️  Please edit .env and add:"
    echo "   1. MONGO_URI (MongoDB Atlas connection string)"
    echo "   2. Your cryptocurrency wallet addresses"
    echo ""
else
    echo "✅ .env already exists"
fi

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "✅ Setup Complete!"
echo ""
echo "🚀 To run Phase 1 locally:"
echo "   Terminal 1: python bot/main.py"
echo "   Terminal 2: python -m uvicorn backend.app:app --reload"
echo ""
echo "📚 See README.md for more details"
