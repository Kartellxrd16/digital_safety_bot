import os
import re # Make sure 're' is imported for regex filters
from telegram import Update, MessageEntity
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import Firebase setup and functions from firebase_config.py
from firebase_config import db # This 'db' is the initialized Firestore client
from firebase_config import get_content

# Import handlers
from handlers.start_help import start_command, help_command
from handlers.quiz import quiz_command, quiz_callback_handler
from handlers.digital_safety import handle_privacy_request, handle_fake_profile_request, handle_scam_request

# Import security scanners
from security_scanners import scan_url

# Define PORT for webhook and check for RENDER_EXTERNAL_HOSTNAME
# Render will provide the PORT environment variable
PORT = int(os.environ.get('PORT', 8000)) # Default to 8000 for local testing if PORT not set

def main():
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
        return

    # Check if Firebase DB initialized successfully (db is set in firebase_config.py)
    if db is None:
        print("Exiting: Firebase DB failed to initialize. Bot cannot operate.")
        return

    application = Application.builder().token(token).build()

    # Register command handlers (these are already case-insensitive for the command name)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quiz", quiz_command))

    # Add MessageHandlers for backslash commands (case-insensitive)
    # FIX: Use (?i) flag inside the regex pattern for case-insensitivity
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^\\start$'), start_command))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^\\help$'), help_command))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^\\quiz$'), quiz_command))

    # Register callback query handler for quiz buttons
    application.add_handler(CallbackQueryHandler(quiz_callback_handler))

    # Handler for scanning URLs (looks for messages containing a URL entity)
    async def handle_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handles messages containing URLs and scans them."""
        # Ensure the message has text and at least one URL entity
        if update.message and update.message.text and update.message.entities:
            # Extract the first URL found in the message
            for entity in update.message.entities:
                if entity.type == MessageEntity.URL:
                    url = update.message.text[entity.offset : entity.offset + entity.length]
                    await update.message.reply_text("🔎 Scanning URL... Please wait. This might take a few seconds.")
                    scan_result = await scan_url(url)
                    await update.message.reply_text(scan_result, parse_mode='Markdown')
                    return # Process only the first URL found and exit

    application.add_handler(MessageHandler(filters.TEXT & filters.Entity(MessageEntity.URL), handle_url_message))

    # Re-adding specific handlers for text keywords (using re.IGNORECASE for robustness)
    # FIX: Use (?i) flag inside the regex pattern for case-insensitivity
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^(privacy|privacy tips)$'), handle_privacy_request))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^(fake profile|fake profiles)$'), handle_fake_profile_request))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)^(scam|scams)$'), handle_scam_request))

    # Fallback handler for any other text messages that don't match previous handlers
    async def unhandled_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Responds to messages that don't match any other handler."""
        if update.message and update.message.text:
            await update.message.reply_text("I'm not sure how to respond to that yet. Try typing 'privacy', 'fake profile', or 'scam', or use /help for commands.")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unhandled_message))


    # CRITICAL CHANGE: Webhook vs. Long Polling based on environment
    # Check if we are running on Render (or a similar cloud platform)
    if os.environ.get("RENDER"): # Render sets a 'RENDER' environment variable
        # For Render, we use webhooks
        WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_HOSTNAME") # Render provides its public URL
        if not WEBHOOK_URL:
            print("RENDER_EXTERNAL_HOSTNAME not found. Cannot set webhook for Render deployment.")
            return

        print(f"Starting bot with webhook at https://{WEBHOOK_URL}/{token}")
        application.run_webhook(
            listen="0.0.0.0", # Listen on all available network interfaces
            port=PORT,         # Use the port provided by Render
            url_path=token,    # Use the bot token as the URL path for security
            webhook_url=f"https://{WEBHOOK_URL}/{token}" # Full URL for Telegram to send updates to
        )
    else:
        # For local development, use long polling
        print("Running bot locally with long polling... Press Ctrl+C to stop.")
        # Ensure Update.ALL_TYPES is imported if used here
        from telegram import Update as TelegramUpdate # Alias to avoid conflict if Update is already imported
        application.run_polling(allowed_updates=TelegramUpdate.ALL_TYPES)

if __name__ == "__main__":
    main()