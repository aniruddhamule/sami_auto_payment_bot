"""
AUTOMATIC TELEGRAM PAID MEMBERSHIP BOT
======================================
✅ Instant access after payment confirmation
✅ One-time use invite links
✅ Automatic channel access
✅ No manual approval needed
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
import os

# Import config
try:
    from config import *
except ImportError:
    print("❌ Error: config.py not found or has errors!")
    print("Please check your config.py file")
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

# Load/Save database functions
def load_db(filename, default=None):
    """Load JSON database from file"""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
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
        logger.error(f"QR Code generation error: {e}")
        return None


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


async def create_single_use_invite_link(context, user_id, username, order_id):
    """Create single-use invite link with expiry"""
    try:
        # Create invite link with expiry and member limit
        expiry_date = datetime.now() + timedelta(hours=INVITE_LINK_EXPIRY_HOURS)
        
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=PREMIUM_CHANNEL_ID,
            expire_date=int(expiry_date.timestamp()),
            member_limit=1,  # Single use only
            name=f"User_{user_id}_{int(time.time())}"
        )
        
        # Store invite link info
        invite_links_db[str(user_id)] = {
            'link': invite_link.invite_link,
            'order_id': order_id,
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


# ============================================================
# BOT HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    # Check if already a member
    if is_member(user.id):
        user_link_data = invite_links_db.get(str(user.id), {})
        invite_link = user_link_data.get('link', PREMIUM_CHANNEL_LINK)
        
        await update.message.reply_text(
            f"✅ *You Already Have Access!*\n\n"
            f"👤 Welcome back, {user.first_name}!\n\n"
            f"🔗 Your invite link:\n{invite_link}\n\n"
            f"If the link has expired, contact admin: {ADMIN_USERNAME}",
            parse_mode='Markdown',
            disable_web_page_preview=True,
            protect_content=True  # Prevent forwarding
        )
        return
    
    welcome_message = f"""
🎉 *Welcome to {BOT_NAME}!* 🎉

Hello {user.first_name}! 👋

Get *Lifetime Premium Access* for just *₹{MEMBERSHIP_PRICE}*! 🚀

✨ *What You'll Get:*
• 📚 Exclusive premium content
• ♾️ Lifetime access (one-time payment)
• 🎯 Instant access after payment
• 🔄 Regular updates

💳 *Simple 3-Step Process:*
1️⃣ Click "Join Membership" below
2️⃣ Scan QR code and pay ₹{MEMBERSHIP_PRICE}
3️⃣ Click "I Have Paid" to get instant access!

🔒 *Features:*
• ⚡ Instant access (no waiting!)
• 🔐 Secure one-time invite link
• 📱 Works with any UPI app
• 💯 100% secure payment

Ready to join? Click below! 👇
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Join Membership", callback_data='join_membership')],
        [InlineKeyboardButton("ℹ️ How It Works", callback_data='how_it_works')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown',
        protect_content=True  # Prevent forwarding
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    if callback_data == 'join_membership':
        await show_membership_plan(query, context)
    elif callback_data == 'get_access':
        await initiate_payment(query, context)
    elif callback_data.startswith('confirm_payment_'):
        order_id = callback_data.replace('confirm_payment_', '')
        await process_payment_confirmation(query, context, order_id)
    elif callback_data == 'contact_admin':
        await contact_admin(query, context)
    elif callback_data == 'how_it_works':
        await show_how_it_works(query, context)
    elif callback_data == 'back_main':
        await back_to_main(query, context)


async def show_how_it_works(query, context):
    """Show how it works"""
    message = f"""
❓ *How It Works*

*Step 1: Get QR Code*
Click "Join Membership" and then "Get Access Now"

*Step 2: Pay via UPI*
Scan the QR code with any UPI app:
• Google Pay
• PhonePe  
• Paytm
• BHIM
• Any other UPI app

*Step 3: Confirm Payment*
After paying ₹{MEMBERSHIP_PRICE}, click "✅ I Have Paid"

*Step 4: Get Instant Access*
You'll immediately receive:
• One-time invite link
• Valid for {INVITE_LINK_EXPIRY_HOURS} hours
• Direct access to premium channel

*Step 5: Join Channel*
Click the link and join the premium channel!

⚡ *Super Fast!* The whole process takes less than 2 minutes!

🔒 *Secure:* Your link works only once and cannot be shared.
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Get Started", callback_data='join_membership')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        # If edit fails, delete and send new
        try:
            await query.message.delete()
        except:
            pass
        await query.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            protect_content=True
        )


async def show_membership_plan(query, context):
    """Show membership plan"""
    user_id = query.from_user.id
    
    # Check if already a member
    if is_member(user_id):
        user_link_data = invite_links_db.get(str(user_id), {})
        invite_link = user_link_data.get('link', PREMIUM_CHANNEL_LINK)
        
        message = (
            f"✅ *You Already Have Access!*\n\n"
            f"🔗 Your invite link:\n{invite_link}\n\n"
            f"If the link has expired, contact: {ADMIN_USERNAME}"
        )
        
        try:
            await query.edit_message_text(
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        except Exception as e:
            logger.error(f"Error editing message: {e}")
            try:
                await query.message.delete()
            except:
                pass
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                protect_content=True
            )
        return
    
    message = f"""
💎 *LIFETIME MEMBERSHIP* 💎

*Price: ₹{MEMBERSHIP_PRICE}* (One-time payment)

✅ *What's Included:*
• 📚 Access to all premium content
• ♾️ Lifetime membership (no renewal)
• ⚡ Instant access after payment
• 🎯 Priority support
• 🔄 Regular content updates
• 🎁 Exclusive benefits

💳 *Payment:*
• Secure UPI payment
• Any UPI app works
• Direct to merchant
• No hidden charges

⚡ *Process:*
1. Pay ₹{MEMBERSHIP_PRICE} via UPI
2. Click "I Have Paid"
3. Get instant invite link
4. Join premium channel

🔒 *Security:*
• One-time use link
• Cannot be shared
• {INVITE_LINK_EXPIRY_HOURS} hours validity
• Secure payment

Ready to get lifetime access?
"""
    
    keyboard = [
        [InlineKeyboardButton(f"💳 Get Access Now - ₹{MEMBERSHIP_PRICE}", callback_data='get_access')],
        [InlineKeyboardButton("❓ How It Works", callback_data='how_it_works')],
        [InlineKeyboardButton("🔙 Back", callback_data='back_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            await query.message.delete()
        except:
            pass
        await query.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            protect_content=True
        )


async def initiate_payment(query, context):
    """Generate QR code and payment instructions"""
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
    # Delete previous message
    try:
        await query.message.delete()
    except Exception as e:
        logger.error(f"Error deleting message: {e}")
    
    # Check if user already has a pending order
    for order_id, order in orders_db.items():
        if order['user_id'] == user_id and order['status'] == 'pending':
            # Reuse existing order
            await show_payment_screen(query, context, order_id, order)
            return
    
    # Generate new order
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
    
    logger.info(f"📦 New order created: {order_id} by user {user_id} ({username})")
    
    await show_payment_screen(query, context, order_id, orders_db[order_id])


async def show_payment_screen(query, context, order_id, order):
    """Display payment QR code and instructions"""
    
    # Generate UPI string and QR code
    upi_string = create_upi_string(order_id, order['amount'])
    qr_image = generate_qr_code(upi_string)
    
    if not qr_image:
        await query.message.reply_text(
            "❌ Error generating QR code. Please try again or contact admin.",
            parse_mode='Markdown',
            protect_content=True
        )
        return
    
    payment_message = f"""
💳 *PAYMENT DETAILS*

📋 *Order ID:* `{order_id}`
💰 *Amount:* ₹{order['amount']}
⏰ *Valid for:* {PAYMENT_EXPIRY_MINUTES} minutes

*📱 HOW TO PAY:*

*Option 1: Scan QR Code* (Recommended)
• Open any UPI app on your phone
• Scan the QR code below
• Pay ₹{order['amount']}
• Come back and click "✅ I Have Paid"

*Option 2: Pay via UPI ID*
• UPI ID: `{UPI_ID}`
• Amount: ₹{order['amount']}
• Note: {order_id}

*⚡ AFTER PAYMENT:*
1. Click "✅ I Have Paid" button below
2. You'll get instant invite link
3. Click the link to join premium channel
4. Start enjoying premium content!

*🔒 Your link will be:*
• Valid for {INVITE_LINK_EXPIRY_HOURS} hours
• One-time use only
• Cannot be shared
• Secure and private

*Need help?* Contact: {ADMIN_USERNAME}
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ I Have Paid - Get Access Now", callback_data=f'confirm_payment_{order_id}')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin_photo')],
        [InlineKeyboardButton("🔙 Cancel", callback_data='back_main_photo')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Send QR code
    try:
        await query.message.reply_photo(
            photo=qr_image,
            caption=payment_message,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            protect_content=True  # Prevent forwarding
        )
    except Exception as e:
        logger.error(f"Error sending payment screen: {e}")
        await query.message.reply_text(
            f"❌ Error displaying payment screen. Please contact admin.\nError: {str(e)}",
            parse_mode='Markdown',
            protect_content=True
        )


async def process_payment_confirmation(query, context, order_id):
    """Process payment confirmation and grant instant access"""
    user_id = query.from_user.id
    username = query.from_user.username or query.from_user.first_name
    
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
    if order['status'] == 'approved':
        user_link_data = invite_links_db.get(str(user_id), {})
        invite_link = user_link_data.get('link', PREMIUM_CHANNEL_LINK)
        
        # Delete QR code message and send new message
        try:
            await query.message.delete()
        except:
            pass
        
        await query.message.reply_text(
            f"✅ *Payment Already Confirmed!*\n\n"
            f"🔗 Your invite link:\n{invite_link}\n\n"
            f"Click the link above to join the premium channel!",
            parse_mode='Markdown',
            disable_web_page_preview=True,
            protect_content=True
        )
        return
    
    # Check if expired
    try:
        expires_at = datetime.fromisoformat(order['expires_at'])
        if datetime.now() > expires_at:
            await query.answer("⏰ Payment window expired! Please create a new order.", show_alert=True)
            return
    except:
        pass
    
    # Delete QR code message
    try:
        await query.message.delete()
    except:
        pass
    
    # Show processing message
    processing_msg = await query.message.reply_text(
        "⏳ *Processing your payment...*\n\n"
        "Please wait while we create your exclusive invite link...",
        parse_mode='Markdown',
        protect_content=True
    )
    
    # Create single-use invite link
    invite_link = await create_single_use_invite_link(
        context,
        user_id,
        username,
        order_id
    )
    
    if not invite_link:
        try:
            await processing_msg.delete()
        except:
            pass
        
        await query.message.reply_text(
            f"❌ *Error Creating Invite Link*\n\n"
            f"Please contact admin: {ADMIN_USERNAME}\n"
            f"Your Order ID: `{order_id}`",
            parse_mode='Markdown',
            protect_content=True
        )
        
        # Notify admin
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"⚠️ Failed to create invite link for Order: {order_id}\nUser: {username} ({user_id})",
                parse_mode='Markdown'
            )
        except:
            pass
        
        return
    
    # Update order status
    orders_db[order_id]['status'] = 'approved'
    orders_db[order_id]['approved_at'] = datetime.now().isoformat()
    orders_db[order_id]['invite_link'] = invite_link
    save_db(ORDERS_FILE, orders_db)
    
    # Add to members
    add_member(user_id, username, order_id)
    
    # Delete processing message
    try:
        await processing_msg.delete()
    except:
        pass
    
    # Send success message with invite link
    success_message = f"""
✅ *PAYMENT CONFIRMED - ACCESS GRANTED!* ✅

🎉 Congratulations! Your payment has been confirmed!

📋 *Order ID:* `{order_id}`
💰 *Amount:* ₹{order['amount']}
✨ *Status:* Approved & Active

*🔗 YOUR EXCLUSIVE INVITE LINK:*

{invite_link}

*⚡ NEXT STEPS:*

1️⃣ Click the link above
2️⃣ Join the premium channel
3️⃣ Start enjoying premium content!

*🔒 IMPORTANT:*
• This link works ONLY ONCE
• Valid for {INVITE_LINK_EXPIRY_HOURS} hours
• Cannot be shared with others
• Use it now to get access!

*⏰ Link Expires:* {(datetime.now() + timedelta(hours=INVITE_LINK_EXPIRY_HOURS)).strftime('%d %b %Y, %I:%M %p')}

Welcome to the premium family! 🚀

*Need help?* Contact: {ADMIN_USERNAME}
"""
    
    keyboard = [
        [InlineKeyboardButton("🔗 Join Premium Channel", url=invite_link)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        success_message,
        reply_markup=reply_markup,
        parse_mode='Markdown',
        disable_web_page_preview=True,
        protect_content=True  # Prevent forwarding
    )
    
    # Notify admin
    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=f"✅ *New Member*\n\n"
                 f"📋 Order: `{order_id}`\n"
                 f"👤 User: {order['first_name']} (@{username})\n"
                 f"🆔 User ID: `{user_id}`\n"
                 f"💰 Amount: ₹{order['amount']}\n"
                 f"⏰ Time: {datetime.now().strftime('%d %b, %I:%M %p')}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error notifying admin: {e}")
    
    logger.info(f"✅ Order {order_id} approved automatically for user {user_id}")


async def contact_admin(query, context):
    """Show admin contact - for text messages"""
    message = f"""
📞 *CONTACT ADMIN*

Need help? Contact our admin:

👤 *Admin:* {ADMIN_USERNAME}

*Common Issues:*
• Payment problems
• Invite link expired
• Technical support
• Refund requests

*Response Time:* Usually within 1-2 hours

Click below to message admin:
"""
    
    keyboard = [
        [InlineKeyboardButton("💬 Message Admin", url=f"https://t.me/{ADMIN_USERNAME.replace('@', '')}")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data='back_main')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            await query.message.delete()
        except:
            pass
        await query.message.reply_text(
            message,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            protect_content=True
        )


async def back_to_main(query, context):
    """Return to main menu - for text messages"""
    user = query.from_user
    
    welcome_message = f"""
🎉 *Welcome back, {user.first_name}!*

Get *Lifetime Premium Access* for just *₹{MEMBERSHIP_PRICE}*! 🚀

✨ *Features:*
• ⚡ Instant access after payment
• 🔒 Secure one-time invite link
• ♾️ Lifetime membership
• 📱 Works with any UPI app

Ready to join? 👇
"""
    
    keyboard = [
        [InlineKeyboardButton("🚀 Join Membership", callback_data='join_membership')],
        [InlineKeyboardButton("ℹ️ How It Works", callback_data='how_it_works')],
        [InlineKeyboardButton("📞 Contact Admin", callback_data='contact_admin')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error editing message: {e}")
        try:
            await query.message.delete()
        except:
            pass
        await query.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown',
            protect_content=True
        )


# ============================================================
# ADMIN COMMANDS
# ============================================================

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bot statistics"""
    user_id = update.effective_user.id
    
    # Check if admin
    if str(user_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    total_orders = len(orders_db)
    approved = sum(1 for o in orders_db.values() if o['status'] == 'approved')
    pending = sum(1 for o in orders_db.values() if o['status'] == 'pending')
    total_members = len(members_db)
    revenue = sum(o['amount'] for o in orders_db.values() if o['status'] == 'approved')
    
    stats_message = f"""
📊 *BOT STATISTICS*

*Orders:*
📦 Total: {total_orders}
✅ Approved: {approved}
⏳ Pending: {pending}

*Members:*
👥 Total: {total_members}
🔗 Active Links: {len(invite_links_db)}

*Revenue:*
💰 Total: ₹{revenue}

*Database:*
📁 Orders: {ORDERS_FILE}
📁 Members: {MEMBERS_FILE}
📁 Links: {INVITE_LINKS_FILE}
"""
    
    await update.message.reply_text(stats_message, parse_mode='Markdown')


async def admin_members(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all members"""
    user_id = update.effective_user.id
    
    # Check if admin
    if str(user_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not members_db:
        await update.message.reply_text("📭 No members yet!")
        return
    
    message = f"👥 *ALL MEMBERS ({len(members_db)})*\n\n"
    
    for uid, member in list(members_db.items())[:20]:  # Show first 20
        message += (
            f"👤 @{member['username']}\n"
            f"🆔 `{uid}`\n"
            f"📋 Order: `{member['order_id']}`\n"
            f"⏰ {member['joined_at'][:10]}\n\n"
        )
    
    if len(members_db) > 20:
        message += f"\n... and {len(members_db) - 20} more members"
    
    await update.message.reply_text(message, parse_mode='Markdown')


async def admin_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List recent orders"""
    user_id = update.effective_user.id
    
    # Check if admin
    if str(user_id) != ADMIN_CHAT_ID:
        await update.message.reply_text("❌ Unauthorized!")
        return
    
    if not orders_db:
        await update.message.reply_text("📭 No orders yet!")
        return
    
    # Get last 10 orders
    recent_orders = sorted(
        orders_db.items(),
        key=lambda x: x[1]['created_at'],
        reverse=True
    )[:10]
    
    message = f"📋 *RECENT ORDERS ({len(recent_orders)})*\n\n"
    
    for order_id, order in recent_orders:
        status_emoji = "✅" if order['status'] == 'approved' else "⏳"
        message += (
            f"{status_emoji} `{order_id}`\n"
            f"👤 {order['first_name']} (@{order.get('username', 'N/A')})\n"
            f"💰 ₹{order['amount']} | {order['status']}\n"
            f"⏰ {order['created_at'][:16]}\n\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Exception while handling an update: {context.error}")


# ============================================================
# MAIN FUNCTION
# ============================================================

def validate_config():
    """Validate configuration"""
    errors = []
    
    if TELEGRAM_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        errors.append("❌ TELEGRAM_BOT_TOKEN not set")
    
    if ADMIN_CHAT_ID == "YOUR_ADMIN_CHAT_ID":
        errors.append("❌ ADMIN_CHAT_ID not set")
    
    if UPI_ID == "your-upi-id@bank":
        errors.append("❌ UPI_ID not set")
    
    if PREMIUM_CHANNEL_ID == -1001234567890:
        errors.append("❌ PREMIUM_CHANNEL_ID not set")
    
    if errors:
        print("\n" + "="*60)
        print("🚫 CONFIGURATION ERRORS:")
        print("="*60)
        for error in errors:
            print(error)
        print("="*60)
        print("\nPlease fix config.py and try again.")
        print("See SETUP_GUIDE.md for help.\n")
        return False
    
    return True


def main():
    """Start the bot"""
    
    # Validate configuration
    if not validate_config():
        exit(1)
    
    print("\n" + "="*60)
    print("🚀 STARTING AUTOMATIC MEMBERSHIP BOT")
    print("="*60)
    print(f"💳 Payment: UPI (₹{MEMBERSHIP_PRICE})")
    print(f"⚡ Access: Automatic (Instant)")
    print(f"🔒 Links: Single-use ({INVITE_LINK_EXPIRY_HOURS}h expiry)")
    print(f"📱 Channel ID: {PREMIUM_CHANNEL_ID}")
    print("="*60 + "\n")
    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # User handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Admin commands
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("members", admin_members))
    application.add_handler(CommandHandler("orders", admin_orders))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("✅ Bot Started Successfully!")
    logger.info(f"💰 Membership Price: ₹{MEMBERSHIP_PRICE}")
    logger.info(f"🔗 Invite Link Expiry: {INVITE_LINK_EXPIRY_HOURS} hours")
    logger.info(f"📱 Premium Channel: {PREMIUM_CHANNEL_ID}")
    
    # Start polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
