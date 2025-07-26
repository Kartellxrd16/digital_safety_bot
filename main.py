import os
import re  # Make sure 're' is imported for regex filters
from telegram import Update, MessageEntity
import telegram
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Import Firebase setup and functions from firebase_config.py
from firebase_config import db  # This 'db' is the initialized Firestore client
from firebase_config import get_content

# Import handlers
from handlers.start_help import start_command, help_command
from handlers.quiz import quiz_command, quiz_callback_handler
from handlers.digital_safety import handle_privacy_request, handle_fake_profile_request, handle_scam_request, report_fake_profile, report_help

# Import security scanners
from security_scanners import scan_url

# Define PORT for webhook and check for RENDER_EXTERNAL_HOSTNAME
PORT = int(os.environ.get('PORT', 8000))  # Default to 8000 for local testing if PORT not set

def main():
    """Start the bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
        return

    if db is None:
        print("Exiting: Firebase DB failed to initialize. Bot cannot operate.")
        return

    try:
        application = Application.builder().token(token).build()

        # Register command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("quiz", quiz_command))
        application.add_handler(CommandHandler("report", report_fake_profile))  # New report command
        application.add_handler(CommandHandler("report_help", report_help))     # New help command

        # Add MessageHandlers for backslash commands
        application.add_handler(MessageHandler(filters.Regex(r'(?i)^\\start$'), start_command))
        application.add_handler(MessageHandler(filters.Regex(r'(?i)^\\help$'), help_command))
        application.add_handler(MessageHandler(filters.Regex(r'(?i)^\\quiz$'), quiz_command))

        # Register callback query handler for quiz buttons
        application.add_handler(CallbackQueryHandler(quiz_callback_handler))

        # Handler for scanning URLs
        async def handle_url_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if update.message and update.message.text and update.message.entities:
                for entity in update.message.entities:
                    if entity.type == MessageEntity.URL:
                        url = update.message.text[entity.offset : entity.offset + entity.length]
                        await update.message.reply_text("🔎 Scanning URL... Please wait. This might take a few seconds.")
                        scan_result = await scan_url(url)
                        await update.message.reply_text(scan_result, parse_mode='Markdown')
                        return
        application.add_handler(MessageHandler(filters.TEXT & filters.Entity(MessageEntity.URL), handle_url_message))

        # Re-adding specific handlers for text keywords
        application.add_handler(MessageHandler(filters.Regex(r'(?i)^(privacy|privacy tips)$'), handle_privacy_request))
        application.add_handler(MessageHandler(filters.Regex(r'(?i)^(fake profile|fake profiles)$'), handle_fake_profile_request))
        application.add_handler(MessageHandler(filters.Regex(r'(?i)^(scam|scams)$'), handle_scam_request))

        # Fallback handler for all messages
        async def unhandled_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
            if update.message:
                if update.message.voice:
                    await update.message.reply_text("I'm not sure how to respond to that yet. Try typing 'privacy', 'fake profile', or 'scam', or use /help for commands.")
                elif update.message.photo:
                    await update.message.reply_text("I'm not sure how to respond to that yet. Try typing 'privacy', 'fake profile', or 'scam', or use /help for commands.")
                elif update.message.text:
                    await update.message.reply_text("I'm not sure how to respond to that yet. Try typing 'privacy', 'fake profile', or 'scam', or use /help for commands.")

        application.add_handler(MessageHandler(
            ~filters.COMMAND & 
            ~filters.Entity(MessageEntity.URL) & 
            ~filters.Regex(r'(?i)^(privacy|privacy tips)$') & 
            ~filters.Regex(r'(?i)^(fake profile|fake profiles)$') & 
            ~filters.Regex(r'(?i)^(scam|scams)$') & 
            (filters.TEXT | filters.VOICE | filters.PHOTO), 
            unhandled_message
        ))

        if os.environ.get("RENDER"):
            WEBHOOK_URL = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
            if not WEBHOOK_URL:
                print("RENDER_EXTERNAL_HOSTNAME not found. Cannot set webhook for Render deployment.")
                return
            print(f"Starting bot with webhook at https://{WEBHOOK_URL}/{token}")
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=token,
                webhook_url=f"https://{WEBHOOK_URL}/{token}"
            )
        else:
            print("Running bot locally with long polling... Press Ctrl+C to stop.")
            application.run_polling(allowed_updates=Update.ALL_TYPES)

    except telegram.error.NetworkError as e:
        logger.error(f"Network error occurred: {e}. Check your internet connection or DNS settings.")
    except Exception as e:
        logger.error(f"Unexpected error during bot startup: {e}")

if __name__ == "__main__":
    main()