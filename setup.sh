#!/bin/bash

echo "╔══════════════════════════════════════════════════════════╗"
echo "║   SEMI-AUTOMATIC MEMBERSHIP BOT - QUICK SETUP            ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not installed!${NC}"
    echo "Install: curl -fsSL https://get.docker.com -o get-docker.sh && sudo sh get-docker.sh"
    exit 1
fi

echo -e "${GREEN}✅ Docker installed${NC}"

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose not installed!${NC}"
    echo "Install: sudo apt install docker-compose -y"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose installed${NC}"
echo ""

# Create directories
echo -e "${YELLOW}📁 Creating directories...${NC}"
mkdir -p data logs
chmod 755 data logs
echo -e "${GREEN}✅ Directories created${NC}"
echo ""

# Check config
if grep -q "YOUR_BOT_TOKEN_HERE" config.py; then
    echo -e "${RED}❌ Please configure config.py first!${NC}"
    echo ""
    echo "Edit config.py and fill in:"
    echo "  - TELEGRAM_BOT_TOKEN"
    echo "  - ADMIN_CHAT_ID"
    echo "  - UPI_ID"
    echo "  - PREMIUM_CHANNEL_ID"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Configuration looks good${NC}"
echo ""

# Build
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
docker-compose build

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build successful${NC}"
echo ""

# Start
echo -e "${YELLOW}🚀 Starting bot...${NC}"
docker-compose up -d

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to start!${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Bot started!${NC}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Commands:"
echo "  docker-compose logs -f    # View logs"
echo "  docker-compose down       # Stop bot"
echo "  docker-compose restart    # Restart bot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
