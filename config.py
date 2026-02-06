"""
TELEGRAM BOT CONFIGURATION
==========================
Complete configuration file with all required fields
"""

# ============================================================
# TELEGRAM BOT SETTINGS
# ============================================================

# Bot Token from @BotFather
TELEGRAM_BOT_TOKEN = "8488665198:AAHpk_3lzzgrjmnruyooqPANitDfQrGSlpE"

# Bot Name (displayed in messages)
BOT_NAME = "Premium Membership Bot"

# ============================================================
# ADMIN SETTINGS
# ============================================================

# Admin Username (with @)
ADMIN_USERNAME = "@Maclustersupports"

# Admin Chat ID (for notifications)
# Get from @userinfobot
ADMIN_CHAT_ID = "8187329376"

# ============================================================
# PAYMENT SETTINGS (UPI - NO FEES!)
# ============================================================

# Membership price in INR
MEMBERSHIP_PRICE = 109

# Your UPI ID for receiving payments
UPI_ID = "aniruddha12@fam"

# Merchant/Business name
MERCHANT_NAME = "Premium Membership"

# Payment window expiry (minutes)
PAYMENT_EXPIRY_MINUTES = 10

# ============================================================
# CHANNEL SETTINGS
# ============================================================

# Premium channel ID (MUST be negative number)
# Get from @userinfobot by forwarding channel message
PREMIUM_CHANNEL_ID = -1002019773776

# Fallback invite link (optional)
PREMIUM_CHANNEL_LINK = "https://t.me/+ElNqgNA939BlMDU1"

# ============================================================
# INVITE LINK SETTINGS
# ============================================================

# Link expiry time (hours)
INVITE_LINK_EXPIRY_HOURS = 24

# ============================================================
# NOTES
# ============================================================
"""
✅ All required fields are configured above
✅ Bot is ready to use
✅ No payment gateway needed
✅ Direct UPI payments only

To deploy:
1. Ensure Docker is installed
2. Run: chmod +x setup.sh
3. Run: ./setup.sh
4. Bot will start automatically

To test:
1. Send /start to your bot
2. Test the complete flow
3. Verify all buttons work
4. Check message cleanup
5. Verify invite links work

Admin Commands:
/stats - View statistics
/members - List all members
/orders - View recent orders
"""
