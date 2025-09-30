import pandas as pd
import logging
import subprocess
import sys
import asyncio
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from datetime import datetime
from typing import List, Dict, Set
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token from environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CSV_FILE = "como_products_scraped.csv"
SUBSCRIBERS_FILE = "subscribers.json"

# Global variables
subscribers: Set[int] = set()
app_instance = None

def load_data():
    """Load Como products data from CSV"""
    try:
        if not os.path.exists(CSV_FILE):
            return None
        df = pd.read_csv(CSV_FILE)
        return df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return None

def load_subscribers():
    """Load subscribers from JSON file"""
    global subscribers
    try:
        if os.path.exists(SUBSCRIBERS_FILE):
            with open(SUBSCRIBERS_FILE, 'r') as f:
                subscriber_list = json.load(f)
                subscribers = set(subscriber_list)
        else:
            subscribers = set()
    except Exception as e:
        logger.error(f"Error loading subscribers: {e}")
        subscribers = set()

def save_subscribers():
    """Save subscribers to JSON file"""
    try:
        with open(SUBSCRIBERS_FILE, 'w') as f:
            json.dump(list(subscribers), f)
    except Exception as e:
        logger.error(f"Error saving subscribers: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_text = """
🏟️ Como 1907 Products Bot

Available commands:
/sizesequence - Show products with non-sequential sizes
/sizetype - Show products with 'option' size type
/refresh - Manually update data
/subscribe - Get automatic notifications
/unsubscribe - Stop notifications

🔔 Auto-refresh: Every hour
📊 Notifications: New products, size changes, discounts

Data from Como Football official shop
    """
    await update.message.reply_text(welcome_text)

async def size_sequence(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sizesequence command - show non-sequential products"""
    df = load_data()

    if df is None:
        await update.message.reply_text("❌ Error loading product data. Please try again later.")
        return

    # Filter non-sequential products and exclude customization products
    exclude_keywords = ['Add Your Name/Number', 'Choose a player', 'Choose a Patch']
    non_sequential = df[df['size_sequential'] == 'No']

    # Exclude products with customization keywords
    for keyword in exclude_keywords:
        non_sequential = non_sequential[~non_sequential['title'].str.contains(keyword, case=False, na=False)]

    if len(non_sequential) == 0:
        await update.message.reply_text("✅ All products have sequential sizes!")
        return

    # Format response
    response = f"🔍 Non-Sequential Size Products ({len(non_sequential)} found)\n\n"

    for idx, row in non_sequential.iterrows():
        product_name = row['title']
        sizes = row['size']

        response += f"• {product_name} ({sizes})\n"

        # Split message if too long (Telegram limit ~4096 chars)
        if len(response) > 3500:
            await update.message.reply_text(response)
            response = ""

    if response:
        await update.message.reply_text(response)

async def size_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /sizetype command - show products with 'option' size type"""
    df = load_data()

    if df is None:
        await update.message.reply_text("❌ Error loading product data. Please try again later.")
        return

    # Filter products with size_type = 'option' and exclude customization products
    exclude_keywords = ['Add Your Name/Number', 'Choose a player', 'Choose a Patch']
    option_products = df[df['size_type'] == 'option']

    # Exclude products with customization keywords
    for keyword in exclude_keywords:
        option_products = option_products[~option_products['title'].str.contains(keyword, case=False, na=False)]

    if len(option_products) == 0:
        await update.message.reply_text("❌ No products found with 'option' size type.")
        return

    # Format response
    response = f"📊 Products with 'option' Size Type ({len(option_products)} found)\n\n"

    for idx, row in option_products.iterrows():
        product_name = row['title']

        response += f"• {product_name}\n"

        # Split message if too long (Telegram limit ~4096 chars)
        if len(response) > 3500:
            await update.message.reply_text(response)
            response = ""

    if response:
        await update.message.reply_text(response)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command - show all available commands"""
    help_text = """
🏟️ Como 1907 Products Bot - Help

Available Commands:

🔍 /sizesequence
Show products with non-sequential sizes

📊 /sizetype
Show products with 'option' size type

🔄 /refresh
Update data from Como Football shop

❓ /help
Show this help message

📋 /start
Welcome message and basic info

---
Data Source: Como Football Official Shop
Total Products: ~343 items
Last Updated: Use /refresh to get latest data
    """
    await update.message.reply_text(help_text)

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command"""
    user_id = update.effective_user.id
    global subscribers

    if user_id in subscribers:
        await update.message.reply_text("✅ You're already subscribed to notifications!")
    else:
        subscribers.add(user_id)
        save_subscribers()
        await update.message.reply_text(
            "🔔 Subscribed! You'll receive notifications for:\n\n"
            "🆕 New products\n"
            "📐 Size sequence changes\n"
            "💰 New discounts\n\n"
            "Auto-refresh: Every hour\n"
            "Use /unsubscribe to stop notifications"
        )

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unsubscribe command"""
    user_id = update.effective_user.id
    global subscribers

    if user_id in subscribers:
        subscribers.remove(user_id)
        save_subscribers()
        await update.message.reply_text("❌ Unsubscribed from notifications")
    else:
        await update.message.reply_text("You're not currently subscribed to notifications")

# Notification System Integration
class ChangeDetector:
    def __init__(self):
        self.history_dir = "notifications/history"
        os.makedirs(self.history_dir, exist_ok=True)
        self.cleanup_old_files()

    def save_current_data(self, csv_file: str = "como_products_scraped.csv") -> str:
        """Save current data with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
        history_file = os.path.join(self.history_dir, f"como_products_{timestamp}.csv")

        df = pd.read_csv(csv_file)
        df.to_csv(history_file, index=False)
        return history_file

    def get_latest_history_file(self) -> str:
        """Get the most recent history file"""
        history_files = [f for f in os.listdir(self.history_dir) if f.endswith('.csv')]
        if not history_files:
            return None
        history_files.sort(reverse=True)
        return os.path.join(self.history_dir, history_files[0])

    def detect_changes(self, current_csv: str = "como_products_scraped.csv") -> Dict[str, List]:
        """Detect changes between current and previous data"""
        previous_file = self.get_latest_history_file()
        if not previous_file:
            return {"new_products": [], "size_changes": [], "new_discounts": []}

        current_df = pd.read_csv(current_csv)
        previous_df = pd.read_csv(previous_file)

        return {
            "new_products": self._detect_new_products(current_df, previous_df),
            "size_changes": self._detect_size_changes(current_df, previous_df),
            "new_discounts": self._detect_new_discounts(current_df, previous_df)
        }

    def _detect_new_products(self, current_df: pd.DataFrame, previous_df: pd.DataFrame) -> List[Dict]:
        """Detect new products"""
        current_ids = set(current_df['product_id'])
        previous_ids = set(previous_df['product_id'])
        new_ids = current_ids - previous_ids

        new_products = []
        for product_id in new_ids:
            product = current_df[current_df['product_id'] == product_id].iloc[0]
            new_products.append({
                'title': product['title'],
                'price': product['current_price']
            })
        return new_products

    def _detect_size_changes(self, current_df: pd.DataFrame, previous_df: pd.DataFrame) -> List[Dict]:
        """Detect size sequence changes"""
        merged = current_df.merge(previous_df, on='product_id', suffixes=('_current', '_previous'))
        size_changes = merged[merged['size_sequential_current'] != merged['size_sequential_previous']]

        changes = []
        for _, row in size_changes.iterrows():
            changes.append({
                'title': row['title_current'],
                'from': row['size_sequential_previous'],
                'to': row['size_sequential_current'],
                'sizes': row['size_current']
            })
        return changes

    def _detect_new_discounts(self, current_df: pd.DataFrame, previous_df: pd.DataFrame) -> List[Dict]:
        """Detect new discounts"""
        merged = current_df.merge(previous_df, on='product_id', suffixes=('_current', '_previous'))
        new_discounts = merged[
            (merged['discount_amount_previous'] == '-') &
            (merged['discount_amount_current'] != '-')
        ]

        discounts = []
        for _, row in new_discounts.iterrows():
            discounts.append({
                'title': row['title_current'],
                'current_price': row['current_price_current'],
                'original_price': row['original_price_current'],
                'discount_percent': row['discount_percent_current']
            })
        return discounts

    def format_notifications(self, changes: Dict[str, List]) -> List[str]:
        """Format changes into notification messages"""
        notifications = []

        if changes['new_products']:
            msg = f"🆕 New Products ({len(changes['new_products'])} found)\n\n"
            for product in changes['new_products']:
                msg += f"• {product['title']} - {product['price']}\n"
            notifications.append(msg)

        if changes['size_changes']:
            msg = f"📐 Size Changes ({len(changes['size_changes'])} found)\n\n"
            for change in changes['size_changes']:
                status = "✅ Fixed" if change['to'] == 'Yes' else "❌ Broken"
                msg += f"• {change['title']} - {status}\n"
            notifications.append(msg)

        if changes['new_discounts']:
            msg = f"💰 New Discounts ({len(changes['new_discounts'])} found)\n\n"
            for discount in changes['new_discounts']:
                msg += f"• {discount['title']}\n"
                msg += f"  {discount['current_price']} (was {discount['original_price']}) - {discount['discount_percent']}\n"
            notifications.append(msg)

        return notifications

    def cleanup_old_files(self, days_to_keep: int = 7):
        """Delete history files older than specified days, keep only 2 most recent"""
        try:
            import time
            current_time = time.time()
            cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)  # 7 days in seconds

            # Get all CSV files in history directory
            history_files = []
            for filename in os.listdir(self.history_dir):
                if filename.endswith('.csv'):
                    file_path = os.path.join(self.history_dir, filename)
                    file_time = os.path.getmtime(file_path)
                    history_files.append((file_path, file_time, filename))

            # Sort by modification time (newest first)
            history_files.sort(key=lambda x: x[1], reverse=True)

            deleted_count = 0
            # Keep only 2 most recent files for comparison, delete rest
            for i, (file_path, file_time, filename) in enumerate(history_files):
                if i >= 2 or file_time < cutoff_time:  # Keep only 2 recent files OR delete old files
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"Deleted old history file: {filename}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} history files (keeping only 2 most recent)")

        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}")

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /refresh command - run scraper and detect changes"""
    await update.message.reply_text("🔄 Refreshing data from Como Football shop...")

    try:
        # Initialize change detector
        detector = ChangeDetector()

        # Run scraper script using subprocess
        result = subprocess.run(
            [sys.executable, 'scrape_como.py'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode == 0:
            # Extract product count from output
            output_lines = result.stdout.strip().split('\n')
            total_products = "Unknown"
            for line in output_lines:
                if "Total products found:" in line:
                    total_products = line.split(":")[-1].strip()
                    break

            # Detect changes
            changes = detector.detect_changes()
            notifications = detector.format_notifications(changes)

            # Send success message
            await update.message.reply_text(
                f"✅ Data refreshed successfully!\n\nTotal products: {total_products}"
            )

            # Send change notifications if any
            if notifications:
                await update.message.reply_text("📢 Changes detected:")
                for notification in notifications:
                    await update.message.reply_text(notification)
            else:
                await update.message.reply_text("📋 No changes since last update")

            # Save current data for next comparison
            detector.save_current_data()

        else:
            # Show error if scraping failed
            error_msg = result.stderr[:500] if result.stderr else "Unknown error occurred"
            await update.message.reply_text(
                f"❌ Error refreshing data:\n\n{error_msg}"
            )

    except subprocess.TimeoutExpired:
        await update.message.reply_text("⏰ Timeout: Scraping took too long (>5 minutes)")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def auto_refresh_and_notify():
    """Background task to auto-refresh data and send notifications"""
    global app_instance
    logger.info("Auto-refresh system started")

    while True:
        try:
            # Wait 1 hour
            await asyncio.sleep(3600)  # 3600 seconds = 1 hour

            logger.info("Running auto-refresh...")

            # Initialize change detector
            detector = ChangeDetector()

            # Run scraper
            result = subprocess.run(
                [sys.executable, 'scrape_como.py'],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                # Detect changes
                changes = detector.detect_changes()
                notifications = detector.format_notifications(changes)

                # Send notifications to all subscribers
                if notifications and subscribers:
                    logger.info(f"Sending notifications to {len(subscribers)} subscribers")

                    for user_id in subscribers.copy():  # Use copy to avoid modification during iteration
                        try:
                            # Send header message
                            await app_instance.bot.send_message(
                                chat_id=user_id,
                                text="🔔 Auto-Update Notification"
                            )

                            # Send each notification
                            for notification in notifications:
                                await app_instance.bot.send_message(
                                    chat_id=user_id,
                                    text=notification
                                )

                        except Exception as e:
                            logger.error(f"Failed to send notification to user {user_id}: {e}")
                            # Remove invalid user IDs (user blocked bot, etc.)
                            if "bot was blocked" in str(e).lower():
                                subscribers.discard(user_id)
                                save_subscribers()

                # Save current data for next comparison
                detector.save_current_data()

                if notifications:
                    logger.info(f"Notifications sent: {len(notifications)} types of changes detected")
                else:
                    logger.info("No changes detected in auto-refresh")
            else:
                logger.error(f"Auto-refresh scraping failed: {result.stderr}")

        except Exception as e:
            logger.error(f"Error in auto-refresh: {e}")

async def post_init(application):
    """Initialize background tasks after bot starts"""
    global app_instance
    app_instance = application
    # Start auto-refresh background task
    application.create_task(auto_refresh_and_notify())

def main():
    """Start the bot"""
    # Load subscribers
    load_subscribers()

    # Create application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("sizesequence", size_sequence))
    application.add_handler(CommandHandler("sizetype", size_type))
    application.add_handler(CommandHandler("refresh", refresh))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))

    # Start the bot
    print("Como Products Bot started!")
    print("Auto-refresh: Every 1 hour")
    print(f"Subscribers loaded: {len(subscribers)}")
    print("Available commands: /start, /help, /sizesequence, /sizetype, /refresh, /subscribe, /unsubscribe")

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()