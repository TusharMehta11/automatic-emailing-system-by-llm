# Automatic Emailing System (LLM)

This repo contains two Python scripts:

- `cus_mail.py`: a Gradio UI that generates a professional email using an LLM + retrieval.
- `direct_mail.py`: polls a Gmail inbox for unread emails, extracts intent with an LLM, generates a reply, saves to MongoDB, and sends the response.

## Prerequisites

- Python installed
- MongoDB (Atlas) connection string
- Gmail account with an **App Password** (recommended) for SMTP/IMAP

## Setup

1) Install dependencies:

```bash
python -m pip install -r requirements.txt
```

2) Create a local `.env` file (DO NOT commit it):

- Copy `.env.example` → `.env`
- Fill in real values:

```env
MONGODB_URI=your_mongodb_uri
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=your_gmail_app_password
```

`direct_mail.py` and `cus_mail.py` use `python-dotenv` to auto-load `.env` on startup.

## Run

### Gradio email generator

```bash
python cus_mail.py
```

### Inbox auto-reply bot

```bash
python direct_mail.py
```

## Security

- Never upload/commit `.env` (it contains secrets). This repo’s `.gitignore` already ignores `.env`.
- If you accidentally pushed credentials to GitHub, rotate them immediately (MongoDB user password + Gmail app password) and remove them from git history.

