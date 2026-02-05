"""
SEMI-AUTOMATIC TELEGRAM PAID MEMBERSHIP BOT
============================================
No payment gateway | No API fees | Manual verification

Features:
✅ QR-code payment display (UPI)
✅ Order ID generation
✅ User payment confirmation button
✅ Manual payment verification by admin
✅ Single-use invite link (1 user only)
✅ Invite link expiry (time-limited)
✅ Automatic channel access after approval
✅ No link sharing / leak protection
✅ User & order logging
✅ No payment gateway fees
"""

import logging
import qrcode
import io
import json
import time
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from config import *

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Simple file-based database (no external dependencies)
ORDERS_FILE = 'data/orders.json'
MEMBERS_FILE = 'data/members.json'
INVITE_LINKS_FILE = 'data/invite_links.json'

# Load databases
def load_db(filename, default=None):
    """Load JSON database from file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return default if default is not None else {}

def save_db(filename, data):
    """Save JSON database to file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2, default=str)

# Initialize databases
orders_db = load_db(ORDERS_FILE, {})
members_db = load_db(MEMBERS_FILE, {})
invite_links_db = load_db(INVITE_LINKS_FILE, {})


# ============================================================
# UTILITY FUNCTIONS
# ============================================================

def generate_order_id():
    """Generate unique order ID"""
    timestamp = int(time.time())
    return f"ORD{timestamp}"


def generate_qr_code(upi_string):
    """Generate QR code image from UPI string"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(upi_string)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    bio = io.BytesIO()
    img.save(bio, 'PNG')
    bio.seek(0)
    return bio


def create_upi_string(order_id, amount):
    """Create UPI payment string"""
    upi_string = (
        f"upi://pay?"
        f"pa={UPI_ID}&"
        f"pn={MERCHANT_NAME}&"
        f"am={amount}&"
        f"tn=Order%20{order_id}&"
        f"cu=INR"
    )
    return upi_string


async def create_single_use_invite_link(context, user_id, username):
    """Create single-use invite link with expiry"""
    try:
        # Create invite link with expiry and member limit
        expiry_date = datetime.now() + timedelta(hours=INVITE_LINK_EXPIRY_HOURS)
        
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=PREMIUM_CHANNEL_ID,
            expire_date=int(expiry_date.timestamp()),
            member_limit=1,  # Single use only
            name=f"Member_{user_id}_{int(time.time())}"
        )
        
        # Store invite link info
        invite_links_db[str(user_id)] = {
            'link': invite_link.invite_link,
            'created_at': datetime.now().isoformat(),
            'expires_at': expiry_date.isoformat(),
            'used': False,
            'username': username
        }
        save_db(INVITE_LINKS_FILE, invite_links_db)
        
        logger.info(f"✅ Created single-use invite link for user {user_id}")
        return invite_link.invite_link
    
    except Exception as e:
        logger.error(f"❌ Error creating invite link: {e}")
        return None


def is_member(user_id):
    """Check if user is already a member"""
    return str(user_id) in members_db


def add_member(user_id, username, order_id):
    """Add user to members database"""
    members_db[str(user_id)] = {
        'username': username,
        'order_id': order_id,
        'joined_at': datetime.now().isoformat(),
        'active': True
    }
    save_db(MEMBERS_FILE, members_db)
    logger.info(f"✅ User {user_id} added to members")


def get_pending_orders():
    """Get all pending orders awaiting admin approval"""
    pending = []
    for order_id, order in orders_db.items():
        if order['status'] == 'awaiting_approval':
            pending.append((order_id, order))
    return pending


# ============================================================
# BOT HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    welcome_message = f"""
🎉 **Welcome to {BOT_NAME}!** 🎉

Hello {user.first_name}! 👋

Get **Lifetime Premium Access** for just **₹{MEMBERSHIP_PRICE}**! 🚀

✨ **What you'll get:**
• Exclusive premium content
• Lifetime access (one-time payment)
• Priority support
• Regular updates

💳 **Simple Payment Process:**
1. Get QR code for UPI payment
2. Pay from any UPI app
3. Click "Payment Done"
4. Admin verifies (usually within 1 hour)
5. Get your exclusive invite link

🔒 **Secure & Protected:**
• Single-use invite link (just for you)
• Link expires after {INVITE_LINK_EXPIRY_HOURS} hours
• No sharing possible
• Secure payment via UPI

Click below to get started! 👇
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Join Membership", callback_data='join_membership')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == 'join_membership':
        await show_membership_plans(query, context)
    elif callback_data == 'select_lifetime':
        await initiate_payment(query, context)
    elif callback_data.startswith('confirm_payment_'):
        order_id = callback_data.replace('confirm_payment_', '')
        await confirm_payment(query, context, order_id)
    elif callback_data == 'contact_admin':
        await contact_admin(query, context)
    elif callback_data == 'back_main':
        await back_to_main(query, context)


async def show_membership_plans(query, context):
    """Show membership plan options"""
    user_id = query.from_user.id
    
    # Check if already a member
    if is_member(user_id):
        user_link = invite_links_db.get(str(user_id), {}).get('link', PREMIUM_CHANNEL_LINK)
        await query.edit_message_text(
            f"✅ You already have **Lifetime Premium Access**!\n\n"
            f"🔗 Your access link:\n{user_link}\n\n"
            f"⚠️ This link is single-use and valid for {INVITE_LINK_EXPIRY_HOURS} hours.",
            parse_mode='Markdown'
        )
        return
    
    message = f"""
💎 **MEMBERSHIP PLAN** 💎

**Lifetime Access – ₹{MEMBERSHIP_PRICE}**

✅ **What's included:**
• Exclusive premium content
• Lifetime access (no renewal)
• Priority support
• Regular updates

💳 **Payment Method:**
• UPI (any UPI app)
• Direct to merchant
• No platform fees
• Secure & instant

🔒 **After Payment:**
• Admin verifies your payment
• You get single-use invite link
• Link valid for {INVITE_LINK_EXPIRY_HOURS} hours
• Access granted immediately

⏱️ **Verification Time:** Usually within 1 hour

Ready to join?
"""
    
    keyboard = [
        [InlineKeyboardButton(f"📦 Get Lifetime Access – ₹{MEMBERSHIP_PRICE}", callback_data='select_lifetime')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def initiate_payment(query, context):
    """Generate QR code and show payment instructions"""
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    # Generate order
    order_id = generate_order_id()
    amount = MEMBERSHIP_PRICE
    
    # Store order in database
    orders_db[order_id] = {
        'user_id': user_id,
        'username': username,
        'first_name': query.from_user.first_name,
        'amount': amount,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(minutes=PAYMENT_EXPIRY_MINUTES)).isoformat()
    }
    save_db(ORDERS_FILE, orders_db)
    
    # Generate UPI string and QR code
    upi_string = create_upi_string(order_id, amount)
    qr_image = generate_qr_code(upi_string)
    
    payment_message = f"""
💳 **PAYMENT INSTRUCTIONS** 💳

📋 **Order ID:** `{order_id}`
💰 **Amount:** ₹{amount}
⏰ **Valid for:** {PAYMENT_EXPIRY_MINUTES} minutes
🎯 **Access:** Lifetime

**📱 HOW TO PAY:**

**Step 1:** Scan the QR code below with any UPI app:
• Google Pay
• PhonePe
• Paytm
• BHIM
• Or any other UPI app

**Step 2:** Complete the payment of **₹{amount}**

**Step 3:** Click the **✅ Payment Done** button below

**Step 4:** Admin will verify your payment (usually within 1 hour)

**Step 5:** You'll receive your single-use invite link

⚠️ **IMPORTANT:**
• QR code expires in {PAYMENT_EXPIRY_MINUTES} minutes
• Pay the exact amount: ₹{amount}
• Click "Payment Done" ONLY after completing payment
• Keep your payment screenshot ready
• Note your Order ID: `{order_id}`

**Direct UPI ID:** `{UPI_ID}`
**Merchant:** {MERCHANT_NAME}
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ I Have Paid – Verify Payment", callback_data=f'confirm_payment_{order_id}')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
        [InlineKeyboardButton("🔙 Cancel", callback_data='back_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send QR code
    await query.message.reply_photo(
        photo=qr_image,
        caption=payment_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    # Delete previous message
    try:
        await query.message.delete()
    except:
        pass
    
    # Log the order
    logger.info(f"📦 New order created: {order_id} by user {user_id} ({username})")


async def confirm_payment(query, context, order_id):
    """User confirms payment - send for admin verification"""
    user_id = query.from_user.id
    
    # Check if order exists
    if order_id not in orders_db:
        await query.answer("❌ Order not found!", show_alert=True)
        return
    
    order = orders_db[order_id]
    
    # Check if order belongs to this user
    if order['user_id'] != user_id:
        await query.answer("❌ This order doesn't belong to you!", show_alert=True)
        return
    
    # Check if already processed
    if order['status'] in ['awaiting_approval', 'verified', 'approved']:
        await query.answer("⏳ Your payment is already under review!", show_alert=True)
        return
    
    # Check if expired
    expires_at = datetime.fromisoformat(order['expires_at'])
    if datetime.now() > expires_at:
        await query.answer("⏰ Payment window expired! Please create a new order.", show_alert=True)
        return
    
    # Update order status
    orders_db[order_id]['status'] = 'awaiting_approval'
    orders_db[order_id]['confirmed_at'] = datetime.now().isoformat()
    save_db(ORDERS_FILE, orders_db)
    
    # Send confirmation to user
    confirmation_message = f"""
✅ **PAYMENT CONFIRMATION RECEIVED**

Thank you! Your payment confirmation has been received.

📋 **Order ID:** `{order_id}`
💰 **Amount:** ₹{order['amount']}
⏰ **Submitted:** Just now
👤 **Status:** Awaiting Admin Verification

**⏳ Next Steps:**

Admin will verify your payment manually and you'll be notified:

**If Approved:**
✅ You'll receive a message with your single-use invite link
✅ Link will be valid for {INVITE_LINK_EXPIRY_HOURS} hours
✅ Use it to join the premium channel

**Verification Time:** Usually within 1 hour

**Need Help?**
Contact admin: {ADMIN_USERNAME}

Your Order ID: `{order_id}`
Keep this for reference!
"""
    
    await query.edit_message_text(
        confirmation_message,
        parse_mode='Markdown'
    )
    
    # Notify admin
    if ADMIN_CHAT_ID:
        await notify_admin_new_payment(context, order_id, order)
    
    logger.info(f"✅ Payment confirmed by user {user_id} for order {order_id}")


async def notify_admin_new_payment(context, order_id, order):
    """Notify admin about new payment to verify"""
    
    admin_message = f"""
🔔 **NEW PAYMENT TO VERIFY** 🔔

📋 **Order ID:** `{order_id}`
👤 **User:** {order['first_name']} (@{order['username']})
🆔 **User ID:** `{order['user_id']}`
💰 **Amount:** ₹{order['amount']}
⏰ **Time:** {order['confirmed_at']}

**⚠️ ACTION REQUIRED:**

Please check your UPI app for payment of ₹{order['amount']} and then:

✅ **If payment received:** Use command:
`/approve {order_id}`

❌ **If payment NOT received:** Use command:
`/reject {order_id}`

**Quick Commands:**
• `/approve {order_id}` - Approve and send invite link
• `/reject {order_id}` - Reject order
• `/pending` - See all pending orders
"""
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f'admin_approve_{order_id}'),
            InlineKeyboardButton("❌ Reject", callback_data=f'admin_reject_{order_id}')
        ],
        [InlineKeyboardButton("📋 View All Pending", callback_data='admin_pending')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        logger.info(f"📤 Admin notified about order {order_id}")
    except Exception as e:
        logger.error(f"❌ Error notifying admin: {e}")


async def contact_admin(query, context):
    """Show admin contact information"""
    message = f"""
📞 **CONTACT ADMIN**

Need help? Contact our admin:

👤 **Admin:** {ADMIN_USERNAME}

**Common Questions:**
• Payment verification status
• Invite link not received
• Technical issues
• Refund requests

**Response Time:** Usually within 1-2 hours

Click below to message admin directly:
"""
    
    keyboard = [
        [InlineKeyboardButton("💬 Message Admin", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔙 Back", callback_data='back_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def back_to_main(query, context):
    """Return to main menu"""
    user = query.from_user
    
    welcome_message = f"""
🎉 **Welcome back, {user.first_name}!** 🎉

Get **Lifetime Premium Access** for just **₹{MEMBERSHIP_PRICE}**! 🚀

💳 Simple UPI payment
✅ Manual verification for security
🔒 Single-use invite link
⏱️ Quick approval (usually 1 hour)

Ready to join?
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Join Membership", callback_data='join_membership')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


# ============================================================
# ADMIN COMMANDS
# ============================================================

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approves payment and sends invite link"""
    user_id = update.effective_user.id
    
    # Check if admin
    if str(user_id) != ADMIN_CHAT_ID and update.effective_user.username != ADMIN_USERNAME.replace('@', ''):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    # Get order ID from command
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/approve ORDER_ID`\n\n"
            "Example: `/approve ORD1706123456`",
            parse_mode='Markdown'
        )
        return
    
    order_id = context.args[0]
    
    if order_id not in orders_db:
        await update.message.reply_text(f"❌ Order ID `{order_id}` not found!", parse_mode='Markdown')
        return
    
    order = orders_db[order_id]
    
    if order['status'] == 'approved':
        await update.message.reply_text(f"⚠️ Order `{order_id}` is already approved!", parse_mode='Markdown')
        return
    
    # Create single-use invite link
    invite_link = await create_single_use_invite_link(
        context,
        order['user_id'],
        order['username']
    )
    
    if not invite_link:
        await update.message.reply_text(
            f"❌ Failed to create invite link for order `{order_id}`\n"
            f"Make sure bot is admin in channel with invite permissions!",
            parse_mode='Markdown'
        )
        return
    
    # Update order status
    orders_db[order_id]['status'] = 'approved'
    orders_db[order_id]['approved_at'] = datetime.now().isoformat()
    orders_db[order_id]['approved_by'] = update.effective_user.username
    orders_db[order_id]['invite_link'] = invite_link
    save_db(ORDERS_FILE, orders_db)
    
    # Add to members
    add_member(order['user_id'], order['username'], order_id)
    
    # Send invite link to user
    user_message = f"""
✅ **PAYMENT VERIFIED - ACCESS GRANTED!** ✅

🎉 Congratulations! Your payment has been verified by admin.

📋 **Order ID:** `{order_id}`
💰 **Amount:** ₹{order['amount']}
✨ **Status:** Approved

**🔗 YOUR EXCLUSIVE INVITE LINK:**

{invite_link}

⚠️ **IMPORTANT - READ CAREFULLY:**

🔒 **This link is ONLY for you**
• Single-use link (works only once)
• Expires in {INVITE_LINK_EXPIRY_HOURS} hours
• Cannot be shared or reused
• Click to join the premium channel

⏰ **Expires:** {(datetime.now() + timedelta(hours=INVITE_LINK_EXPIRY_HOURS)).strftime('%d %b %Y, %I:%M %p')}

👉 Click the link above NOW to join!

Welcome to the premium family! 🚀

Questions? Contact: {ADMIN_USERNAME}
"""
    
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=user_message,
            parse_mode='Markdown'
        )
        
        # Confirm to admin
        await update.message.reply_text(
            f"✅ **Order Approved Successfully!**\n\n"
            f"📋 Order: `{order_id}`\n"
            f"👤 User: {order['first_name']} (@{order['username']})\n"
            f"🆔 User ID: `{order['user_id']}`\n"
            f"💰 Amount: ₹{order['amount']}\n"
            f"🔗 Invite link sent to user\n"
            f"⏰ Link expires in {INVITE_LINK_EXPIRY_HOURS} hours",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Order {order_id} approved by admin")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error sending message to user: {e}")
        logger.error(f"❌ Error sending invite link: {e}")


async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects payment"""
    user_id = update.effective_user.id
    
    # Check if admin
    if str(user_id) != ADMIN_CHAT_ID and update.effective_user.username != ADMIN_USERNAME.replace('@', ''):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    # Get order ID
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/reject ORDER_ID [reason]`\n\n"
            "Example: `/reject ORD1706123456 Payment not received`",
            parse_mode='Markdown'
        )
        return
    
    order_id = context.args[0]
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Payment verification failed"
    
    if order_id not in orders_db:
        await update.message.reply_text(f"❌ Order ID `{order_id}` not found!", parse_mode='Markdown')
        return
    
    order = orders_db[order_id]
    
    # Update order status
    orders_db[order_id]['status'] = 'rejected'
    orders_db[order_id]['rejected_at'] = datetime.now().isoformat()
    orders_db[order_id]['rejected_by'] = update.effective_user.username
    orders_db[order_id]['reject_reason'] = reason
    save_db(ORDERS_FILE, orders_db)
    
    # Notify user
    user_message = f"""
❌ **PAYMENT VERIFICATION FAILED**

We're sorry, but your payment could not be verified.

📋 **Order ID:** `{order_id}`
💰 **Amount:** ₹{order['amount']}
❌ **Status:** Rejected

**Reason:** {reason}

**What to do next:**

1. Check your UPI app - payment might have failed
2. If payment was successful, contact admin with:
   • Order ID: `{order_id}`
   • Payment screenshot
   • Transaction ID

3. You can create a new order if needed

Contact admin: {ADMIN_USERNAME}

We apologize for the inconvenience.
"""
    
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=user_message,
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(
            f"✅ Order rejected and user notified\n\n"
            f"📋 Order: `{order_id}`\n"
            f"❌ Reason: {reason}",
            parse_mode='Markdown'
        )
        
        logger.info(f"❌ Order {order_id} rejected by admin: {reason}")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all pending orders"""
    user_id = update.effective_user.id
    
    # Check if admin
    if str(user_id) != ADMIN_CHAT_ID and update.effective_user.username != ADMIN_USERNAME.replace('@', ''):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    pending = get_pending_orders()
    
    if not pending:
        await update.message.reply_text("✅ No pending orders!")
        return
    
    message = f"📋 **PENDING ORDERS ({len(pending)})**\n\n"
    
    for order_id, order in pending:
        message += (
            f"**Order:** `{order_id}`\n"
            f"👤 {order['first_name']} (@{order['username']})\n"
            f"🆔 User ID: `{order['user_id']}`\n"
            f"💰 ₹{order['amount']}\n"
            f"⏰ {order['confirmed_at']}\n"
            f"**Action:** `/approve {order_id}` or `/reject {order_id}`\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    user_id = update.effective_user.id
    
    # Check if admin
    if str(user_id) != ADMIN_CHAT_ID and update.effective_user.username != ADMIN_USERNAME.replace('@', ''):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    total_orders = len(orders_db)
    approved = sum(1 for o in orders_db.values() if o['status'] == 'approved')
    pending = sum(1 for o in orders_db.values() if o['status'] == 'awaiting_approval')
    rejected = sum(1 for o in orders_db.values() if o['status'] == 'rejected')
    total_members = len(members_db)
    revenue = sum(o['amount'] for o in orders_db.values() if o['status'] == 'approved')
    
    stats_message = f"""
📊 **BOT STATISTICS**

**Orders:**
📦 Total: {total_orders}
✅ Approved: {approved}
⏳ Pending: {pending}
❌ Rejected: {rejected}

**Members:**
👥 Total: {total_members}
🔗 Invite Links: {len(invite_links_db)}

**Revenue:**
💰 Total: ₹{revenue}

**Commands:**
`/pending` - View pending orders
`/approve ORDER_ID` - Approve order
`/reject ORDER_ID` - Reject order
`/stats` - View statistics
`/members` - List all members
"""
    
    await update.message.reply_text(stats_message, parse_mode='Markdown')


async def admin_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all members"""
    user_id = update.effective_user.id
    
    # Check if admin
    if str(user_id) != ADMIN_CHAT_ID and update.effective_user.username != ADMIN_USERNAME.replace('@', ''):
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not members_db:
        await update.message.reply_text("📭 No members yet!")
        return
    
    message = f"👥 **ALL MEMBERS ({len(members_db)})**\n\n"
    
    for user_id, member in members_db.items():
        message += (
            f"👤 @{member['username']}\n"
            f"🆔 `{user_id}`\n"
            f"📋 Order: `{member['order_id']}`\n"
            f"⏰ {member['joined_at']}\n\n"
        )
        
        if len(message) > 3500:  # Telegram message limit
            await update.message.reply_text(message, parse_mode='Markdown')
            message = ""
    
    if message:
        await update.message.reply_text(message, parse_mode='Markdown')


# ============================================================
# MAIN FUNCTION
# ============================================================

def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # User handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Admin commands
    application.add_handler(CommandHandler("approve", admin_approve))
    application.add_handler(CommandHandler("reject", admin_reject))
    application.add_handler(CommandHandler("pending", admin_pending))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("members", admin_members))
    
    logger.info("🚀 Semi-Automatic Bot Started!")
    logger.info("💳 Payment: UPI (No Gateway Fees)")
    logger.info("✅ Verification: Manual by Admin")
    logger.info("🔒 Links: Single-use with expiry")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
