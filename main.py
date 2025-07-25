import os
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
# --- CRITICAL CHANGE: Import specific handlers for keyword responses ---
from handlers.digital_safety import handle_privacy_request, handle_fake_profile_request, handle_scam_request
# --- END CRITICAL CHANGE ---

# Import security scanners
from security_scanners import scan_url

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

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("quiz", quiz_command))

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

    # --- CRITICAL CHANGE: Re-adding specific handlers for text keywords ---
    # These handlers use regex for case-insensitive matching of keywords
    application.add_handler(MessageHandler(filters.Regex(r'(?i)\bprivacy\b') | filters.Regex(r'(?i)privacy tips'), handle_privacy_request))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)\bfake profile\b') | filters.Regex(r'(?i)\bfake profiles\b'), handle_fake_profile_request))
    application.add_handler(MessageHandler(filters.Regex(r'(?i)\bscam\b') | filters.Regex(r'(?i)scams\b'), handle_scam_request))
    # --- END CRITICAL CHANGE ---

    # Fallback handler for any other text messages that don't match previous handlers
    async def unhandled_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Responds to messages that don't match any other handler."""
        await update.message.reply_text("I'm not sure how to respond to that yet. Try typing 'privacy', 'fake profile', or 'scam', or use /help for commands.")
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unhandled_message))


    # Run the bot until you press Ctrl-C
    print("Bot is running... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()