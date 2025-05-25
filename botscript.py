from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import subprocess
import whisper
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import google.generativeai as genai
import pickle
import re
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Load the Whisper model once
model = whisper.load_model("base")

# Email configuration
EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# Gemini API configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Google Calendar API setup
SCOPES = ['https://www.googleapis.com/auth/calendar']
CREDENTIALS_FILE = 'credentials.json'
TOKEN_FILE = 'token.pickle'

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return build('calendar', 'v3', credentials=creds)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! I can help you with:\n"
        "1. Drafting emails (use /email)\n"
        "2. Setting calendar events (use /schedule)\n"
        "Just send me a voice or text message after using these commands!"
    )

async def email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'email'
    context.user_data['email_step'] = 'collect_all'
    await update.message.reply_text(
        "Please provide the following details in one message, separated by a new line or comma:\n"
        "1. Recipient's email address\n2. Subject\n3. Main points or context for your email\n\n"
        "Example:\nrecipient@example.com\nSubject of the email\nMain points or context for the email."
    )

async def handle_email_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE, message_text: str):
    step = context.user_data.get('email_step')
    if step == 'collect_all':
        # Try to split by newlines first, then by comma if only one line
        parts = [p.strip() for p in message_text.split('\n') if p.strip()]
        if len(parts) < 3:
            parts = [p.strip() for p in message_text.split(',') if p.strip()]
        if len(parts) < 3:
            await update.message.reply_text(
                "Please provide all three details: recipient, subject, and main points/context, separated by new lines or commas."
            )
            return
        context.user_data['recipient'] = parts[0]
        context.user_data['subject'] = parts[1]
        context.user_data['body'] = parts[2]
        await draft_email_with_gemini(update, context)
        context.user_data['email_step'] = 'confirmation_or_change'
    elif step == 'confirmation_or_change':
        text = message_text.strip().lower()
        if text == 'yes':
            await handle_email_confirmation(update, context)
        elif text == 'no':
            await update.message.reply_text("❌ Email cancelled. Use /email to start over.")
            context.user_data.clear()
        elif text in ['recipient', 'subject', 'body']:
            context.user_data['change_field'] = text
            await update.message.reply_text(f"Please provide the new value for {text}:")
            context.user_data['email_step'] = 'change_value'
        else:
            await update.message.reply_text(
                "Reply with 'yes' to send, 'no' to cancel, or type 'recipient', 'subject', or 'body' to change that field."
            )
    elif step == 'change_value':
        field = context.user_data.get('change_field')
        if field in ['recipient', 'subject', 'body']:
            context.user_data[field] = message_text.strip()
            await draft_email_with_gemini(update, context)
            context.user_data['email_step'] = 'confirmation_or_change'
        else:
            await update.message.reply_text("Invalid field. Please type /email to start over.")
            context.user_data.clear()
    else:
        await update.message.reply_text("Something went wrong. Please start again with /email.")

async def draft_email_with_gemini(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        recipient = context.user_data.get('recipient')
        subject = context.user_data.get('subject')
        body_context = context.user_data.get('body')

        model = genai.GenerativeModel('gemini-2.0-flash')
        prompt = f"""Please draft a professional email with the following details:\nRecipient: {recipient}\nSubject: {subject}\nContext/Points to include: {body_context}\n\nPlease format the email professionally, including appropriate greetings and closings.\nMake sure the tone is professional and the content is clear and concise."""
        response = model.generate_content(prompt)
        drafted_body = response.text

        await update.message.reply_text(
            f"📧 Here's the drafted email:\n\n"
            f"To: {recipient}\n"
            f"Subject: {subject}\n\n"
            f"{drafted_body}\n\n"
            f"Would you like to send this email?\n"
            f"Reply with 'yes' to send, 'no' to cancel, or type 'recipient', 'subject', or 'body' to change that field."
        )
        context.user_data['drafted_email'] = {
            'recipient': recipient,
            'subject': subject,
            'body': drafted_body
        }
    except Exception as e:
        await update.message.reply_text(f"❌ Error drafting email: {str(e)}")

async def handle_email_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.lower() == 'yes':
        try:
            email_data = context.user_data.get('drafted_email')
            msg = MIMEMultipart()
            msg['From'] = EMAIL_ADDRESS
            msg['To'] = email_data['recipient']
            msg['Subject'] = email_data['subject']
            msg.attach(MIMEText(email_data['body'], 'plain'))

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
                smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                smtp.send_message(msg)
            
            await update.message.reply_text("✅ Email has been sent successfully!")
            context.user_data.clear()
        except Exception as e:
            await update.message.reply_text(f"❌ Error sending email: {str(e)}")
    else:
        await update.message.reply_text("❌ Email cancelled. Use /email to start over.")
        context.user_data.clear()

async def schedule_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'schedule'
    await update.message.reply_text("Please send a voice message with your schedule details. Include event title, date, and time.")

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    ogg_path = "voice_message.ogg"
    wav_path = "voice_message.wav"
    file = await context.bot.get_file(voice.file_id)
    await file.download_to_drive(ogg_path)
    subprocess.run(["ffmpeg", "-i", ogg_path, "-ar", "16000", wav_path], check=True)
    result = model.transcribe(wav_path)
    transcription = result["text"]
    mode = context.user_data.get('mode')
    if mode == 'email':
        await handle_email_conversation(update, context, transcription)
    elif mode == 'schedule':
        await process_schedule(update, transcription)
    else:
        await update.message.reply_text(f"📝 Transcription:\n{transcription}")
    os.remove(ogg_path)
    os.remove(wav_path)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get('mode')
    if mode == 'email':
        if context.user_data.get('email_step') == 'confirmation':
            await handle_email_confirmation(update, context)
        else:
            await handle_email_conversation(update, context, update.message.text)
    elif mode == 'schedule':
        await update.message.reply_text("Please use voice for scheduling for now.")
    else:
        await update.message.reply_text("Send /email to draft an email or /schedule to set a calendar event.")

async def process_schedule(update: Update, transcription: str):
    try:
        service = get_calendar_service()
        event = {
            'summary': transcription.split('on')[0].strip(),
            'start': {
                'dateTime': datetime.now().isoformat(),
                'timeZone': 'UTC',
            },
            'end': {
                'dateTime': datetime.now().isoformat(),
                'timeZone': 'UTC',
            },
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        await update.message.reply_text(f"✅ Event created: {event.get('htmlLink')}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error creating calendar event: {str(e)}")

async def list_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Get list of available models
        models = genai.list_models()
        
        # Format the response with names and supported methods
        response = "🤖 Available Gemini Models:\n\n"
        for model in models:
            methods = ', '.join(model.supported_generation_methods)
            response += f"📌 Model: {model.name}\n"
            response += f"Methods: {methods}\n"
            response += "---\n"
            
        # Check if the message is too long and truncate if necessary
        if len(response) > 4000: # Keep a buffer for safety
            response = response[:4000] + "\n... (Message truncated due to length limit)"
        
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text(f"❌ Error listing models: {str(e)}")

def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("email", email_handler))
    app.add_handler(CommandHandler("schedule", schedule_handler))
    app.add_handler(CommandHandler("models", list_models))
    app.add_handler(MessageHandler(filters.VOICE, voice_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
