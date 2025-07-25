import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from firebase_config import get_content # Ensure this import path is correct

# Constants for quiz state management
QUIZ_STATE = "QUIZ_STATE"
CURRENT_QUESTION_INDEX = "CURRENT_QUESTION_INDEX"
CORRECT_ANSWERS_COUNT = "CORRECT_ANSWERS_COUNT"
QUIZ_DATA = "QUIZ_DATA"
QUIZ_TOPIC = "QUIZ_TOPIC"

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with inline buttons for quiz topics."""
    keyboard = [
        [InlineKeyboardButton("Fake Profiles 🕵️‍♀️", callback_data="start_quiz_fake_profile")],
        [InlineKeyboardButton("Digital Privacy 🛡️", callback_data="start_quiz_privacy")]
        # Add more quiz topics here as you create their documents in Firestore
        # Example: [InlineKeyboardButton("Scam Awareness 🚨", callback_data="start_quiz_scam_awareness")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a quiz topic:", reply_markup=reply_markup)

async def _send_question(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_id: str) -> None:
    """Sends the current quiz question to the user."""
    user_data = context.user_data
    quiz_data = user_data.get(QUIZ_DATA)
    current_index = user_data.get(CURRENT_QUESTION_INDEX, 0)

    # Check if quiz is finished
    if current_index >= len(quiz_data["questions"]):
        await _end_quiz(update, context)
        return

    question = quiz_data["questions"][current_index]
    question_text = question["question_text"]
    options = question["options"]

    keyboard = []
    # Ensure options are always sorted by key (A, B, C, D) for consistent display
    sorted_options_keys = sorted(options.keys())
    for key in sorted_options_keys:
        # Callback data format: quiz_topic_prefix|question_id|selected_option
        callback_data = f"{quiz_id}|{question['question_id']}|{key}"
        keyboard.append([InlineKeyboardButton(f"{key}. {options[key]}", callback_data=callback_data)])

    reply_markup = InlineKeyboardMarkup(keyboard)

    # Determine if we should edit the previous message or send a new one
    # This is important for smooth UX, avoiding multiple messages for each question
    if update.callback_query and update.callback_query.message:
        try:
            # Edit the message if it's a callback query (e.g., after answering a question)
            await update.callback_query.edit_message_text(
                text=f"**Question {current_index + 1}:**\n{question_text}",
                reply_markup=reply_markup,
                parse_mode='Markdown' # Use Markdown for bolding
            )
        except Exception as e:
            # Fallback if message cannot be edited (e.g., too old, user deleted it, or Telegram API error)
            print(f"Error editing message to {update.callback_query.message.chat_id}: {e}. Sending new message instead.")
            await update.callback_query.message.reply_text(
                text=f"**Question {current_index + 1}:**\n{question_text}",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    elif update.message:
        # Send a new message if it's the initial quiz_command or other non-callback trigger
        await update.message.reply_text(
            text=f"**Question {current_index + 1}:**\n{question_text}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def _end_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ends the quiz and displays the final score."""
    user_data = context.user_data
    correct_count = user_data.get(CORRECT_ANSWERS_COUNT, 0)
    quiz_data = user_data.get(QUIZ_DATA)
    total_questions = len(quiz_data["questions"]) if quiz_data and "questions" in quiz_data else 0

    # Customize the quiz topic display for the end message based on stored QUIZ_TOPIC
    quiz_topic_display = "your quiz"
    current_quiz_topic = user_data.get(QUIZ_TOPIC)
    if current_quiz_topic == "fake_profile":
        quiz_topic_display = "the Fake Profile Quiz"
    elif current_quiz_topic == "privacy":
        quiz_topic_display = "the Digital Privacy Quiz"
    # Add more conditions here for other quizzes if you add them later

    final_message = (
        f"🎉 Quiz Complete! 🎉\n"
        f"You answered {correct_count} out of {total_questions} questions correctly in {quiz_topic_display}!\n\n"
        "Great job! Would you like to try another quiz or learn more with /help?"
    )

    # Clear user data for the quiz
    user_data.pop(QUIZ_STATE, None)
    user_data.pop(CURRENT_QUESTION_INDEX, None)
    user_data.pop(CORRECT_ANSWERS_COUNT, None)
    user_data.pop(QUIZ_DATA, None)
    user_data.pop(QUIZ_TOPIC, None)

    # Send the final message, preferably by replying to the last message or sending a new one
    if update.callback_query and update.callback_query.message:
        await update.callback_query.message.reply_text(final_message)
    elif update.message:
        await update.message.reply_text(final_message)


async def quiz_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles callback queries (button presses) from quizzes."""
    query = update.callback_query
    await query.answer() # Acknowledge the callback query immediately

    user_data = context.user_data
    callback_data = query.data

    # --- Logic for starting a new quiz ---
    if callback_data.startswith("start_quiz_"):
        quiz_topic_prefix = callback_data.replace("start_quiz_", "") # Extracts "fake_profile" or "privacy"
        quiz_doc_id = f"{quiz_topic_prefix}_quiz" # Constructs the document ID, e.g., "fake_profile_quiz"

        # Initialize quiz state in user_data
        user_data[QUIZ_STATE] = True
        user_data[CURRENT_QUESTION_INDEX] = 0
        user_data[CORRECT_ANSWERS_COUNT] = 0
        user_data[QUIZ_TOPIC] = quiz_topic_prefix # Store the topic for context (e.g., "fake_profile")

        try:
            # Get quiz data from Firestore (synchronous call as before)
            _, quiz_doc = get_content("quizzes", quiz_doc_id)

            if quiz_doc and "questions" in quiz_doc and len(quiz_doc["questions"]) > 0:
                # Shuffle questions to make each quiz fresh and assign to user_data
                quiz_doc["questions"] = random.sample(quiz_doc["questions"], len(quiz_doc["questions"]))
                user_data[QUIZ_DATA] = quiz_doc

                # Get title for the starting message, defaulting to a friendly name
                quiz_title = quiz_doc.get('title', quiz_topic_prefix.replace('_', ' ').title() + " Quiz")

                # Edit the message to show the quiz starting and the first question
                await query.edit_message_text(f"Starting the {quiz_title}! Get ready... 💪")
                # Immediately send the first question
                await _send_question(update, context, quiz_topic_prefix)
            else:
                await query.message.reply_text("Sorry, I couldn't load that quiz or it has no questions right now. Please try again later. 😔")
                user_data.pop(QUIZ_STATE, None) # Clear state if quiz couldn't load
        except Exception as e:
            print(f"Error loading quiz '{quiz_doc_id}': {e}")
            await query.message.reply_text("Sorry, there was an error loading that quiz. Please try again later. 😔")
            user_data.pop(QUIZ_STATE, None) # Clear state on error
        return # Important to return here after handling quiz start

    # --- Logic for answering an existing question ---
    # If not starting a quiz, it must be an answer to an existing question
    if not user_data.get(QUIZ_STATE):
        # This handles cases where user clicks a button from a quiz that was already finished/cleared
        await query.message.reply_text("It looks like you're not currently in a quiz. Please start one with /quiz! 🤔")
        return

    # Parse callback data for an answer: quiz_topic|question_id|selected_option
    parts = callback_data.split('|')
    if len(parts) != 3:
        # Log unexpected data format for debugging (shouldn't happen with correct button generation)
        print(f"Unexpected callback data format (incorrect number of parts): {callback_data}")
        await query.message.reply_text("There was an error processing your answer. Please try again. 🤔")
        return

    quiz_topic_prefix_from_callback = parts[0]
    question_id = parts[1]
    selected_option = parts[2]

    # Ensure the answer is for the currently active quiz and topic
    if user_data.get(QUIZ_TOPIC) != quiz_topic_prefix_from_callback:
        await query.message.reply_text("It looks like you clicked a button from a previous quiz. Please use the buttons for the current quiz! 😅")
        return

    quiz_data = user_data.get(QUIZ_DATA)
    current_index = user_data.get(CURRENT_QUESTION_INDEX, 0)
    correct_count = user_data.get(CORRECT_ANSWERS_COUNT, 0)

    # Robust check: If quiz data is missing or current index is out of bounds, end gracefully
    if not quiz_data or "questions" not in quiz_data or current_index >= len(quiz_data["questions"]):
        await _end_quiz(update, context) # End the quiz if state is inconsistent
        return

    current_question = quiz_data["questions"][current_index]

    # Validate that the answer is for the expected question (based on question_id)
    if current_question["question_id"] == question_id:
        is_correct = (selected_option == current_question["correct_answer"])
        if is_correct:
            correct_count += 1
            user_data[CORRECT_ANSWERS_COUNT] = correct_count
            feedback_message = f"That's correct! ✅\n"
        else:
            feedback_message = (
                f"Not quite. ❌ The correct answer was **{current_question['correct_answer']}**. \n"
                f"Explanation: {current_question['explanation']}\n"
            )

        # Append feedback to the question message and remove buttons
        try:
            # Telegram Bot API's MarkdownV2 requires escaping specific characters if they are literal
            escaped_feedback = feedback_message.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[')
            await query.edit_message_text(
                text=f"{query.message.text_markdown_v2}\n\n{escaped_feedback}",
                reply_markup=None, # Remove buttons after answer
                parse_mode='MarkdownV2' # Use MarkdownV2 for parsing
            )
        except Exception as e:
            print(f"Error editing message: {e} - Falling back to reply_text.")
            await query.message.reply_text(f"{feedback_message}")


        # Move to the next question
        user_data[CURRENT_QUESTION_INDEX] = current_index + 1
        # Send the next question (or end quiz if all questions answered)
        await _send_question(update, context, user_data.get(QUIZ_TOPIC))
    else:
        # If user clicks an old button from a previous question that's not the current one
        await query.message.reply_text("Please answer the *current* question. It looks like you clicked an old button. 🤔")