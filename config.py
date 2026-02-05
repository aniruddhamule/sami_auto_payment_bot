"""
SEMI-AUTOMATIC BOT CONFIGURATION
=================================
Simple UPI payment | No gateway fees | Manual verification
"""

# ============================================================
# TELEGRAM BOT SETTINGS
# ============================================================

# Get this from @BotFather
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Bot name
BOT_NAME = "Premium Membership Bot"

# ============================================================
# ADMIN SETTINGS
# ============================================================

# Admin Telegram username (with @)
ADMIN_USERNAME = "@Maclustersupports"

# Admin Chat ID (for notifications)
# Get from @userinfobot
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"

# ============================================================
# PAYMENT SETTINGS (UPI - NO FEES!)
# ============================================================

# Membership price in INR
MEMBERSHIP_PRICE = 99

# Your UPI ID for receiving payments
UPI_ID = "your-upi-id@bank"  # Example: "9876543210@paytm"

# Merchant/Business name
MERCHANT_NAME = "Premium Membership"

# Payment window expiry (minutes)
PAYMENT_EXPIRY_MINUTES = 60

# ============================================================
# CHANNEL SETTINGS
# ============================================================

# Premium channel ID (numeric)
# Forward a message from channel to @userinfobot to get ID
PREMIUM_CHANNEL_ID = -1001234567890  # Replace with your channel ID

# Fallback invite link
PREMIUM_CHANNEL_LINK = "https://t.me/+YOUR_CHANNEL_LINK"

# ============================================================
# INVITE LINK SETTINGS
# ============================================================

# Single-use invite link expiry (hours)
INVITE_LINK_EXPIRY_HOURS = 24

# ============================================================
# NOTES
# ============================================================
"""
SETUP INSTRUCTIONS:

1. CREATE BOT:
   - Message @BotFather on Telegram
   - Send /newbot
   - Get your bot token
   - Paste above as TELEGRAM_BOT_TOKEN

2. GET ADMIN CHAT ID:
   - Message @userinfobot
   - It will send your User ID
   - Paste above as ADMIN_CHAT_ID

3. SETUP UPI:
   - Use your personal/business UPI ID
   - Format: mobile@upi or name@bank
   - Example: 9876543210@paytm

4. SETUP CHANNEL:
   - Create a PRIVATE Telegram channel
   - Add bot as administrator
   - Give bot "Invite Users via Link" permission
   - Forward message to @userinfobot to get channel ID
   - Paste above as PREMIUM_CHANNEL_ID (negative number)

5. CRITICAL:
   - Bot MUST be admin in channel
   - Bot MUST have "Invite Users via Link" permission
   - Channel must be PRIVATE

6. HOW IT WORKS:
   - User pays to your UPI
   - User clicks "Payment Done"
   - You get notification
   - You check your UPI app
   - You run: /approve ORDER_ID
   - Bot creates single-use invite link
   - User gets link and joins
   - Link becomes invalid

7. NO FEES:
   - Direct UPI payment to your account
   - No payment gateway fees
   - No API costs
   - 100% payment to you

8. SECURITY:
   - Manual verification prevents fraud
   - Single-use links prevent sharing
   - Link expiry adds time limit
   - Full control over who joins
"""
