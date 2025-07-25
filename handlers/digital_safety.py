from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from firebase_config import get_content # Corrected import path

# --- NEW: Separate handlers for each keyword ---

async def handle_privacy_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles requests for privacy tips."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    text_lower = update.message.text.lower()
    
    response_text = "Sorry, I couldn't find detailed privacy tips right now. Please try again later. 😔"

    # Handle Specific Privacy Topics
    if "privacy facebook" in text_lower:
        _, privacy_info = get_content("digital_safety_content", "privacy_tips")
        if privacy_info and "facebook_tips" in privacy_info:
            response_text = f"Here are some specific privacy tips for Facebook: 📱\n\n{privacy_info['facebook_tips']}"
    elif "privacy instagram" in text_lower:
        _, privacy_info = get_content("digital_safety_content", "privacy_tips")
        if privacy_info and "instagram_tips" in privacy_info:
            response_text = f"Here are some specific privacy tips for Instagram: 📸\n\n{privacy_info['instagram_tips']}"
    elif "privacy whatsapp" in text_lower:
        _, privacy_info = get_content("digital_safety_content", "privacy_tips")
        if privacy_info and "whatsapp_tips" in privacy_info:
            response_text = f"Here are some specific privacy tips for WhatsApp: 💬\n\n{privacy_info['whatsapp_tips']}"
    elif "privacy passwords" in text_lower or "strong passwords" in text_lower or "password tips" in text_lower:
        _, privacy_info = get_content("digital_safety_content", "privacy_tips")
        if privacy_info and "password_tips" in privacy_info:
            response_text = f"Here are some tips for creating strong, unique passwords: 🔐\n\n{privacy_info['password_tips']}"
    elif "privacy app permissions" in text_lower or "app permissions" in text_lower:
        _, privacy_info = get_content("digital_safety_content", "privacy_tips")
        if privacy_info and "app_permission_tips" in privacy_info:
            response_text = f"Here's what you need to know about app permissions: ⚙️\n\n{privacy_info['app_permission_tips']}"
    # Fallback to general privacy tips if no specific platform/topic is mentioned
    elif "privacy" in text_lower or "privacy tips" in text_lower: # This catches the general 'privacy'
        _, privacy_info = get_content("digital_safety_content", "privacy_tips")
        if privacy_info and "tips" in privacy_info: # 'tips' is your general privacy field
            response_text = (
                f"Great! Let's talk about privacy. 🛡️ Here are some general tips:\n\n{privacy_info['tips']}\n\n"
                "For more specific advice, try asking about a platform like 'privacy facebook', 'privacy instagram', or 'privacy whatsapp'. "
                "You can also ask about 'privacy passwords' or 'privacy app permissions'."
            )
    
    await update.message.reply_text(response_text)


async def handle_fake_profile_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles requests for fake profile tips."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    
    _, fake_profile_info = get_content("digital_safety_content", "fake_profile_tips")
    if fake_profile_info:
        tips = fake_profile_info.get("tips", "No fake profile tips found.")
        response_text = f"Spotting fake profiles is key! Here are some things to look for: 🕵️‍♀️\n\n{tips}"
    else:
        response_text = "Sorry, I couldn't find detailed fake profile tips right now. 😔"
    
    await update.message.reply_text(response_text)


async def handle_scam_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles requests for scam prevention tips."""
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    _, scam_info = get_content("digital_safety_content", "scam_tips")
    if scam_info:
        tips = scam_info.get("tips", "No scam tips found.")
        response_text = f"Scams are tricky. Here's what you need to know: 🚨\n\n{tips}"
    else:
        response_text = "Sorry, I couldn't find detailed scam prevention tips right now. 😔"
    
    await update.message.reply_text(response_text)

# --- END NEW ---