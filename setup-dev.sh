#!/bin/bash
# Setup development environment

echo "🛠️  GHW Development Environment Setup"
echo "====================================="
echo ""

# Check if .env exists
if [ -f .env ]; then
    echo "✅ .env file already exists"
    echo "Current content:"
    cat .env
    echo ""
    read -p "Do you want to overwrite it? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Setup cancelled"
        exit 1
    fi
fi

# Prompt for values
echo "Enter your Telegram Bot Token (from @BotFather):"
read -r TOKEN

# Create .env
cat > .env << EOF
ENVIRONMENT=dev
TELEGRAM_TOKEN=$TOKEN
EOF

echo ""
echo "✅ .env created successfully!"
echo "📍 Environment: DEV (using ghw-dev.db)"
echo ""
echo "Next steps:"
echo "1. Install dependencies: pip install -r requirements-bot.txt"
echo "2. Run bot: python main.py"
echo "3. (Optional) Dashboard: streamlit run dashboard_v2.py"
echo ""
echo "⚠️  .env is in .gitignore - never commit it!"
