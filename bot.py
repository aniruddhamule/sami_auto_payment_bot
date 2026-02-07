"""
SEMI-AUTOMATIC TELEGRAM PAID MEMBERSHIP BOT
============================================
✅ Manual admin approval (prevents fraud)
✅ Payment screenshot verification
✅ One-time use invite links
✅ Secure payment process
✅ Admin controls everything

Version: 2.1 SEMI-AUTO
Date: 2026-02-07
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
    MessageHandler,
    filters,
    ContextTypes,
)
import os

# Import config
try:
    from config import *
except ImportError:
    print("❌ Error: config.py not found!")
    exit(1)

# Setup logging
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Database files
ORDERS_FILE = 'data/orders.json'
MEMBERS_FILE = 'data/members.json'
INVITE_LINKS_FILE = 'data/invite_links.json'

def load_db(filename, default=None):
    """Load JSON database"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except:
        return default if default is not None else {}

def save_db(filename, data):
    """Save JSON database"""
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving {filename}: {e}")

# Initialize databases
orders_db = load_db(ORDERS_FILE, {})
members_db = load_db(MEMBERS_FILE, {})
invite_links_db = load_db(INVITE_LINKS_FILE, {})


def generate_order_id():
    """Generate unique order ID"""
    return f"ORD{int(time.time())}"


def generate_qr_code(upi_string):
    """Generate QR code"""
    try:
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(upi_string)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio
    except Exception as e:
        logger.error(f"QR error: {e}")
        return None


def create_upi_string(order_id, amount):
    """Create UPI payment string"""
    return (
        f"upi://pay?"
        f"pa={UPI_ID}&"
        f"pn={MERCHANT_NAME}&"
        f"am={amount}&"
        f"tn=Order%20{order_id}&"
        f"cu=INR"
    )


async def create_single_use_invite_link(context, user_id, username, order_id):
    """Create one-time invite link"""
    try:
        expiry_date = datetime.now() + timedelta(hours=INVITE_LINK_EXPIRY_HOURS)
        
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=PREMIUM_CHANNEL_ID,
            expire_date=int(expiry_date.timestamp()),
            member_limit=1,
            name=f"User_{user_id}_{int(time.time())}"
        )
        
        invite_links_db[str(user_id)] = {
            'link': invite_link.invite_link,
            'order_id': order_id,
            'created_at': datetime.now().isoformat(),
            'expires_at': expiry_date.isoformat(),
            'used': False,
            'username': username
        }
        save_db(INVITE_LINKS_FILE, invite_links_db)
        
        logger.info(f"✅ Link created for user {user_id}")
        return invite_link.invite_link
    except Exception as e:
        logger.error(f"❌ Link error: {e}")
        return None


def is_member(user_id):
    """Check if user is member"""
    return str(user_id) in members_db


def add_member(user_id, username, order_id):
    """Add member to database"""
    members_db[str(user_id)] = {
        'username': username,
        'order_id': order_id,
        'joined_at': datetime.now().isoformat(),
        'active': True
    }
    save_db(MEMBERS_FILE, members_db)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start"""
    user = update.effective_user
    
    if is_member(user.id):
        user_link_data = invite_links_db.get(str(user.id), {})
        invite_link = user_link_data.get('link', PREMIUM_CHANNEL_LINK)
        
        await update.message.reply_text(
            f"✅ *You Already Have Access!*\n\n"
            f"🔗 Your link:\n{invite_link}\n\n"
            f"Contact: {ADMIN_USERNAME}",
            parse_mode='Markdown',
            protect_content=True
        )
        return
    
    welcome_message = f"""
🎉 *Welcome to {BOT_NAME}!* 🎉

Hello {user.first_name}! 👋

Get *Lifetime Premium Access* for just *₹{MEMBERSHIP_PRICE}*! 🚀

✨ *What You'll Get:*
• 📚 Exclusive premium content
• ♾️ Lifetime access
• 🎯 Fast approval (within hours)
• 🔄 Regular updates

💳 *Payment Process:*
1️⃣ Click "Join Membership"
2️⃣ Pay ₹{MEMBERSHIP_PRICE} via UPI
3️⃣ Send payment screenshot
4️⃣ Admin approves
5️⃣ Get instant access!

Ready to join? 👇
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Join Membership", callback_data='join_membership')],
        [InlineKeyboardButton("ℹ️ How It Works", callback_data='how_it_works')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
    ]
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown',
        protect_content=True
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle buttons"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'join_membership':
        await show_membership_plan(query, context)
    elif query.data == 'get_access':
        await initiate_payment(query, context)
    elif query.data.startswith('confirm_payment_'):
        order_id = query.data.replace('confirm_payment_', '')
        await request_screenshot(query, context, order_id)
    elif query.data == 'contact_admin':
        await contact_admin(query, context)
    elif query.data == 'how_it_works':
        await show_how_it_works(query, context)
    elif query.data == 'back_main':
        await back_to_main(query, context)


async def show_how_it_works(query, context):
    """Show instructions"""
    message = f"""
❓ *How It Works*

*Step 1: Join Membership*
Click "Join Membership" button

*Step 2: Get QR Code*
Click "Get Access Now" to see payment QR

*Step 3: Pay via UPI*
Scan QR with any UPI app and pay ₹{MEMBERSHIP_PRICE}

*Step 4: Send Screenshot*
Click "✅ I Have Paid" and send payment screenshot

*Step 5: Admin Approval*
Admin verifies payment (usually within 1-2 hours)

*Step 6: Get Access*
After approval, you get one-time invite link

*Step 7: Join Channel*
Click link and join premium channel!

⚡ *Safe & Secure!* Admin verifies every payment.

🔒 *One-time links* - Cannot be shared.
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Get Started", callback_data='join_membership')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_main')],
    ]
    
    # Check if message has text (text message) or photo (photo message)
    if query.message.text:
        # It's a text message, can edit
        try:
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Edit error: {e}")
    else:
        # It's a photo message, delete and send new
        chat_id = query.message.chat_id
        try:
            await query.message.delete()
        except:
            pass
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown',
                protect_content=True
            )
        except Exception as e:
            logger.error(f"Send error: {e}")


async def show_membership_plan(query, context):
    """Show plan"""
    user_id = query.from_user.id
    
    if is_member(user_id):
        try:
            await query.edit_message_text(
                "✅ You already have access!",
                parse_mode='Markdown'
            )
        except:
            try:
                await query.message.delete()
            except:
                pass
            await query.message.reply_text(
                "✅ You already have access!",
                parse_mode='Markdown',
                protect_content=True
            )
        return
    
    message = f"""
💎 *LIFETIME MEMBERSHIP* 💎

*Price: ₹{MEMBERSHIP_PRICE}* (One-time)

✅ *Included:*
• 📚 All premium content
• ♾️ Lifetime access
• ⚡ Fast approval
• 🎯 Priority support
• 🔄 Updates

💳 *Payment:*
• Secure UPI
• Any UPI app works
• Screenshot verification
• Admin approval

🔒 *Security:*
• Manual verification
• One-time links
• {INVITE_LINK_EXPIRY_HOURS}h validity
• Safe & secure

Ready?
"""
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Get Access - ₹{MEMBERSHIP_PRICE}", callback_data='get_access')],
        [InlineKeyboardButton("❓ How It Works", callback_data='how_it_works')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_main')],
    ]
    
    try:
        # Try to edit text message
        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    except:
        # If it's a photo message, delete and send new
        try:
            await query.message.delete()
        except:
            pass
        await query.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown',
            protect_content=True
        )


async def initiate_payment(query, context):
    """Show payment QR"""
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    # Check for existing pending order
    for order_id, order in orders_db.items():
        if order['user_id'] == user_id and order['status'] == 'pending':
            await show_payment_screen(query, context, order_id, order)
            return
    
    # Create new order
    order_id = generate_order_id()
    
    orders_db[order_id] = {
        'user_id': user_id,
        'username': username,
        'first_name': query.from_user.first_name,
        'amount': MEMBERSHIP_PRICE,
        'status': 'pending',
        'created_at': datetime.now().isoformat(),
        'screenshot_uploaded': False
    }
    save_db(ORDERS_FILE, orders_db)
    
    logger.info(f"📦 Order {order_id} created by {username}")
    
    await show_payment_screen(query, context, order_id, orders_db[order_id])


async def show_payment_screen(query, context, order_id, order):
    """Display QR code"""
    
    upi_string = create_upi_string(order_id, order['amount'])
    qr_image = generate_qr_code(upi_string)
    
    if not qr_image:
        await query.message.reply_text(
            f"❌ Error! Contact: {ADMIN_USERNAME}",
            parse_mode='Markdown'
        )
        return
    
    payment_message = f"""
💳 *PAYMENT DETAILS*

📋 *Order ID:* `{order_id}`
💰 *Amount:* ₹{order['amount']}

*📱 INSTRUCTIONS:*

1️⃣ Scan QR code with UPI app
2️⃣ Pay ₹{order['amount']}
3️⃣ Take screenshot of payment
4️⃣ Click "✅ I Have Paid" below
5️⃣ Send screenshot to bot
6️⃣ Wait for admin approval

*⏰ Approval Time:* 1-2 hours

*UPI ID:* `{UPI_ID}`

*Need help?* {ADMIN_USERNAME}
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ I Have Paid", callback_data=f'confirm_payment_{order_id}')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
    ]
    
    try:
        await query.message.reply_photo(
            photo=qr_image,
            caption=payment_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown',
            protect_content=True
        )
    except Exception as e:
        logger.error(f"Error: {e}")


async def request_screenshot(query, context, order_id):
    """Request payment screenshot"""
    user_id = query.from_user.id
    
    if order_id not in orders_db:
        await query.answer("❌ Order not found!", show_alert=True)
        return
    
    order = orders_db[order_id]
    
    if order['user_id'] != user_id:
        await query.answer("❌ Not your order!", show_alert=True)
        return
    
    if order['status'] == 'approved':
        await query.answer("✅ Already approved!", show_alert=True)
        return
    
    # Update order
    orders_db[order_id]['waiting_screenshot'] = True
    save_db(ORDERS_FILE, orders_db)
    
    # Store order_id in context for screenshot handler
    context.user_data['waiting_order_id'] = order_id
    
    message = f"""
📸 *SEND PAYMENT SCREENSHOT*

Please send a clear screenshot of your payment.

*Order ID:* `{order_id}`
*Amount:* ₹{order['amount']}

⏳ *After sending:*
Admin will verify and approve within 1-2 hours.

*Need help?* {ADMIN_USERNAME}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔙 Back", callback_data='back_main')],
    ]
    
    # Get chat_id before deleting
    chat_id = query.message.chat_id
    
    # Delete the QR code photo message
    try:
        await query.message.delete()
    except Exception as e:
        logger.error(f"Could not delete message: {e}")
    
    # Send new text message using bot.send_message (not query.message.reply_text)
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown',
            protect_content=True
        )
    except Exception as e:
        logger.error(f"Could not send message: {e}")
    
    # Notify admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"⏳ *Payment Screenshot Requested*\n\n"
                 f"📋 Order: `{order_id}`\n"
                 f"👤 User: {order['first_name']} (@{order['username']})\n"
                 f"💰 Amount: ₹{order['amount']}\n\n"
                 f"Waiting for screenshot...",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Could not notify admin: {e}")


async def handle_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle screenshot upload"""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    
    # Check if waiting for screenshot
    order_id = context.user_data.get('waiting_order_id')
    if not order_id:
        return
    
    if order_id not in orders_db:
        return
    
    order = orders_db[order_id]
    
    if order['user_id'] != user_id:
        return
    
    # Mark screenshot received
    orders_db[order_id]['screenshot_uploaded'] = True
    orders_db[order_id]['screenshot_time'] = datetime.now().isoformat()
    save_db(ORDERS_FILE, orders_db)
    
    # Clear waiting status
    context.user_data.pop('waiting_order_id', None)
    
    # Confirm to user
    await update.message.reply_text(
        f"✅ *Screenshot Received!*\n\n"
        f"📋 Order: `{order_id}`\n\n"
        f"⏳ Your payment is under review.\n"
        f"Admin will approve within 1-2 hours.\n\n"
        f"You'll get a notification when approved!\n\n"
        f"Thank you for your patience! 🙏",
        parse_mode='Markdown',
        protect_content=True
    )
    
    # Forward to admin with approval buttons
    try:
        if update.message.photo:
            await context.bot.send_photo(
                chat_id=ADMIN_CHAT_ID,
                photo=update.message.photo[-1].file_id,
                caption=f"💳 *PAYMENT SCREENSHOT*\n\n"
                        f"📋 Order: `{order_id}`\n"
                        f"👤 User: {order['first_name']} (@{username})\n"
                        f"🆔 User ID: `{user_id}`\n"
                        f"💰 Amount: ₹{order['amount']}\n"
                        f"⏰ Time: {datetime.now().strftime('%d %b, %I:%M %p')}\n\n"
                        f"*Verify payment and approve:*\n"
                        f"`/approve {order_id}`\n\n"
                        f"*Or reject:*\n"
                        f"`/reject {order_id}`",
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"📸 *Screenshot Received* (but not a photo)\n\n"
                     f"Order: `{order_id}`\n"
                     f"User: {username} ({user_id})\n\n"
                     f"Use: `/approve {order_id}`",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Admin notification error: {e}")


async def approve_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approves order"""
    user_id = update.effective_user.id
    
    # Check admin
    if str(user_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    # Get order ID
    if not context.args:
        await update.message.reply_text(
            "Usage: `/approve ORDER_ID`\n\n"
            "Example: `/approve ORD1234567890`",
            parse_mode='Markdown'
        )
        return
    
    order_id = context.args[0]
    
    if order_id not in orders_db:
        await update.message.reply_text(f"❌ Order `{order_id}` not found!", parse_mode='Markdown')
        return
    
    order = orders_db[order_id]
    
    if order['status'] == 'approved':
        await update.message.reply_text(f"✅ Order `{order_id}` already approved!", parse_mode='Markdown')
        return
    
    # Create invite link
    invite_link = await create_single_use_invite_link(
        context,
        order['user_id'],
        order['username'],
        order_id
    )
    
    if not invite_link:
        await update.message.reply_text(
            f"❌ *Error Creating Link!*\n\n"
            f"Order: `{order_id}`\n\n"
            f"Check:\n"
            f"1. Bot is admin in channel\n"
            f"2. Has 'Invite Users' permission\n"
            f"3. Channel is PRIVATE",
            parse_mode='Markdown'
        )
        return
    
    # Update order
    orders_db[order_id]['status'] = 'approved'
    orders_db[order_id]['approved_at'] = datetime.now().isoformat()
    orders_db[order_id]['invite_link'] = invite_link
    save_db(ORDERS_FILE, orders_db)
    
    # Add to members
    add_member(order['user_id'], order['username'], order_id)
    
    # Send link to user
    try:
        success_message = f"""
✅ *PAYMENT APPROVED - ACCESS GRANTED!* ✅

🎉 Congratulations {order['first_name']}!

📋 *Order ID:* `{order_id}`
💰 *Amount:* ₹{order['amount']}
✨ *Status:* Approved

━━━━━━━━━━━━━━━━━━━━━━━━

*🔗 YOUR EXCLUSIVE INVITE LINK:*

{invite_link}

━━━━━━━━━━━━━━━━━━━━━━━━

*CLICK LINK TO JOIN CHANNEL NOW!*

*🔒 IMPORTANT:*
• Works ONLY ONCE
• Valid for {INVITE_LINK_EXPIRY_HOURS} hours
• Cannot be shared

Welcome! 🚀
"""
        
        keyboard = [
            [InlineKeyboardButton("🔗 Join Premium Channel", url=invite_link)],
        ]
        
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=success_message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown',
            protect_content=True
        )
    except Exception as e:
        logger.error(f"Error sending to user: {e}")
    
    # Confirm to admin
    await update.message.reply_text(
        f"✅ *Approved!*\n\n"
        f"Order: `{order_id}`\n"
        f"User: {order['first_name']} (@{order['username']})\n"
        f"Link sent to user!\n\n"
        f"Link: {invite_link}",
        parse_mode='Markdown'
    )
    
    logger.info(f"✅ Order {order_id} approved by admin")


async def reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin rejects order"""
    user_id = update.effective_user.id
    
    if str(user_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: `/reject ORDER_ID`", parse_mode='Markdown')
        return
    
    order_id = context.args[0]
    
    if order_id not in orders_db:
        await update.message.reply_text(f"❌ Order `{order_id}` not found!", parse_mode='Markdown')
        return
    
    order = orders_db[order_id]
    
    # Update status
    orders_db[order_id]['status'] = 'rejected'
    orders_db[order_id]['rejected_at'] = datetime.now().isoformat()
    save_db(ORDERS_FILE, orders_db)
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=f"❌ *Payment Verification Failed*\n\n"
                 f"Order: `{order_id}`\n\n"
                 f"Your payment could not be verified.\n\n"
                 f"Please contact admin: {ADMIN_USERNAME}",
            parse_mode='Markdown'
        )
    except:
        pass
    
    await update.message.reply_text(
        f"❌ Rejected!\n\nOrder: `{order_id}`\nUser notified.",
        parse_mode='Markdown'
    )


async def pending_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show pending orders"""
    user_id = update.effective_user.id
    
    if str(user_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    pending = [o for o in orders_db.items() if o[1]['status'] == 'pending']
    
    if not pending:
        await update.message.reply_text("📭 No pending orders!")
        return
    
    message = f"⏳ *PENDING ORDERS ({len(pending)})*\n\n"
    
    for order_id, order in pending[:10]:
        screenshot = "✅" if order.get('screenshot_uploaded') else "❌"
        message += (
            f"📋 `{order_id}`\n"
            f"👤 {order['first_name']} (@{order.get('username', 'N/A')})\n"
            f"💰 ₹{order['amount']}\n"
            f"📸 Screenshot: {screenshot}\n"
            f"⏰ {order['created_at'][:16]}\n\n"
            f"Approve: `/approve {order_id}`\n"
            f"Reject: `/reject {order_id}`\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show stats"""
    user_id = update.effective_user.id
    
    if str(user_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    total_orders = len(orders_db)
    approved = sum(1 for o in orders_db.values() if o['status'] == 'approved')
    pending = sum(1 for o in orders_db.values() if o['status'] == 'pending')
    rejected = sum(1 for o in orders_db.values() if o['status'] == 'rejected')
    total_members = len(members_db)
    revenue = sum(o['amount'] for o in orders_db.values() if o['status'] == 'approved')
    
    stats_message = f"""
📊 *BOT STATISTICS*

*Orders:*
📦 Total: {total_orders}
✅ Approved: {approved}
⏳ Pending: {pending}
❌ Rejected: {rejected}

*Members:*
👥 Total: {total_members}
🔗 Active Links: {len(invite_links_db)}

*Revenue:*
💰 Total: ₹{revenue}

*System:*
🔧 Mode: Semi-Automatic
🛡️ Verification: Manual
"""
    
    await update.message.reply_text(stats_message, parse_mode='Markdown')


async def contact_admin(query, context):
    """Contact admin"""
    message = f"""
📞 *CONTACT ADMIN*

Need help?

👤 Admin: {ADMIN_USERNAME}

Click below to message:
"""
    
    keyboard = [
        [InlineKeyboardButton("💬 Message Admin", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔙 Back", callback_data='back_main')],
    ]
    
    # Check if message has text (text message) or photo (photo message)
    if query.message.text:
        # It's a text message, can edit
        try:
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Edit error: {e}")
    else:
        # It's a photo message, delete and send new
        chat_id = query.message.chat_id
        try:
            await query.message.delete()
        except:
            pass
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown',
                protect_content=True
            )
        except Exception as e:
            logger.error(f"Send error: {e}")


async def back_to_main(query, context):
    """Back to main"""
    user = query.from_user
    
    message = f"""
🎉 *Welcome back, {user.first_name}!*

Get Lifetime Access for ₹{MEMBERSHIP_PRICE}! 🚀

Ready to join? 👇
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Join Membership", callback_data='join_membership')],
        [InlineKeyboardButton("ℹ️ How It Works", callback_data='how_it_works')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
    ]
    
    # Check if message has text (text message) or photo (photo message)
    if query.message.text:
        # It's a text message, can edit
        try:
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Edit error: {e}")
    else:
        # It's a photo message, delete and send new
        chat_id = query.message.chat_id
        try:
            await query.message.delete()
        except:
            pass
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown',
                protect_content=True
            )
        except Exception as e:
            logger.error(f"Send error: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Error: {context.error}")


def validate_config():
    """Validate config"""
    errors = []
    
    try:
        _ = TELEGRAM_BOT_TOKEN
        if 'YOUR_BOT_TOKEN' in TELEGRAM_BOT_TOKEN or len(TELEGRAM_BOT_TOKEN) < 10:
            errors.append("❌ TELEGRAM_BOT_TOKEN invalid")
    except NameError:
        errors.append("❌ TELEGRAM_BOT_TOKEN not found")
    
    try:
        _ = ADMIN_CHAT_ID
    except NameError:
        errors.append("❌ ADMIN_CHAT_ID not found")
    
    try:
        _ = UPI_ID
        if 'your-upi-id' in UPI_ID.lower() or '@' not in UPI_ID:
            errors.append("❌ UPI_ID invalid")
    except NameError:
        errors.append("❌ UPI_ID not found")
    
    try:
        _ = PREMIUM_CHANNEL_ID
        if PREMIUM_CHANNEL_ID >= 0:
            errors.append("❌ PREMIUM_CHANNEL_ID must be negative")
    except NameError:
        errors.append("❌ PREMIUM_CHANNEL_ID not found")
    
    try:
        _ = BOT_NAME
    except NameError:
        globals()['BOT_NAME'] = "Premium Membership Bot"
    
    try:
        _ = ADMIN_USERNAME
    except NameError:
        globals()['ADMIN_USERNAME'] = "@admin"
    
    if errors:
        print("\n" + "="*70)
        print("🚫 CONFIGURATION ERRORS")
        print("="*70)
        for error in errors:
            print(error)
        print("="*70)
        return False
    
    return True


def main():
    """Start bot"""
    
    if not validate_config():
        exit(1)
    
    print("\n" + "="*70)
    print("🚀 SEMI-AUTOMATIC MEMBERSHIP BOT")
    print("="*70)
    print(f"💳 Payment: UPI (₹{MEMBERSHIP_PRICE})")
    print(f"🔒 Verification: Manual (Admin Approval)")
    print(f"🔗 Links: One-time use ({INVITE_LINK_EXPIRY_HOURS}h)")
    print(f"📱 Channel: {PREMIUM_CHANNEL_ID}")
    print(f"👨‍💼 Admin: {ADMIN_USERNAME}")
    print("")
    print("✨ FEATURES:")
    print("   ✅ Payment screenshot verification")
    print("   ✅ Manual admin approval")
    print("   ✅ One-time invite links")
    print("   ✅ Fraud prevention")
    print("="*70 + "\n")
    
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # User handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_screenshot))
    
    # Admin commands
    application.add_handler(CommandHandler("approve", approve_order))
    application.add_handler(CommandHandler("reject", reject_order))
    application.add_handler(CommandHandler("pending", pending_orders))
    application.add_handler(CommandHandler("stats", admin_stats))
    
    application.add_error_handler(error_handler)
    
    logger.info("✅ Semi-Auto Bot Started!")
    logger.info(f"💰 Price: ₹{MEMBERSHIP_PRICE}")
    logger.info(f"🔒 Mode: Manual Approval")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
