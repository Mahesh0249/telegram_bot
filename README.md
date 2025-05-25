# Telegram AI Assistant Bot

A powerful Telegram bot that helps users draft emails and manage calendar events using voice commands and AI capabilities.

## Features

- 📧 Email Drafting: Uses Gemini AI to draft professional emails
- 🗓️ Calendar Management: Schedule events using voice commands
- 🎤 Voice Recognition: Convert voice messages to text using Whisper AI
- 🤖 AI Integration: Powered by Google's Gemini AI for intelligent responses

## Prerequisites

- Python 3.8 or higher
- Telegram Bot Token
- Google Cloud Project with Calendar API enabled
- Gemini API Key
- Gmail account for sending emails

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/telegram-ai-assistant.git
cd telegram-ai-assistant
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the project root and add:
```
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
GEMINI_API_KEY=your_gemini_api_key
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_specific_password
```

5. Set up Google Calendar API:
- Download your credentials file from Google Cloud Console
- Rename it to `credentials.json` and place it in the project root

## Usage

1. Start the bot:
```bash
python botscript.py
```

2. In Telegram, use the following commands:
- `/start` - Get started with the bot
- `/email` - Start drafting an email
- `/schedule` - Schedule a calendar event
- `/models` - List available Gemini AI models

## Security Notes

- Never commit sensitive information like API keys or credentials
- Use environment variables for all sensitive data
- Keep your `credentials.json` and `token.pickle` files secure and never share them

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details. 