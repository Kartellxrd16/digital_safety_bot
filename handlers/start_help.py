from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from gtts import gTTS
import os

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message with a voice note."""
    user = update.effective_user
    welcome_message = (
        f"Hello {user.first_name} ❤️!\n"
        "I'm your Digital Self-Defense Chatbot. I can help you learn about:\n"
        "🛡️ Privacy Controls\n"
        "👹 Identifying Fake Profiles\n"
        "🚫 Avoiding Scams\n\n"
        "To get started, simply type 'privacy', 'fake profile', or 'scam'. You can also send me a suspicious link to scan! 🔎\n"
        "Type /help to see more options!"
    )

    # Convert welcome message to speech
    tts = gTTS(text=welcome_message, lang='en')
    audio_file = 'welcome_message.mp3'
    tts.save(audio_file)

    # Send the text message first
    await update.message.reply_text(welcome_message)

    # Show 'sending audio...' status while uploading
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_VOICE)
    await update.effective_chat.send_voice(voice=open(audio_file, 'rb')) # Changed to send_voice for better compatibility

    # Clean up the generated audio file
    os.remove(audio_file)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with available commands and topics."""
    help_text = (
        "Here are the things I can help you with:\n"
        "- Type 'privacy' or 'privacy tips' to learn about setting privacy controls.\n"
        "- Type 'fake profile' to get tips on identifying suspicious accounts.\n"
        "- Type 'scam' or 'scams' to understand common scams and how to avoid them.\n"
        "- Type /quiz to test your knowledge with interactive quizzes! 🧠\n"
        "- Type /start to see the welcome message again."
    )
    await update.message.reply_text(help_text)