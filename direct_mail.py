import email
from os import name
from urllib import response
import ollama
import imaplib
import smtplib
from email.mime.text import MIMEText
import json
from pymongo import MongoClient
from datetime import datetime, time
import time
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer as st
from langchain_community.document_loaders import TextLoader

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("Missing MONGODB_URI env var (set it in environment or in a local .env).")

GMAIL_ADDRESS = os.environ.get("GMAIL_ADDRESS")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD")
if not GMAIL_ADDRESS or not GMAIL_APP_PASSWORD:
    raise RuntimeError("Missing GMAIL_ADDRESS and/or GMAIL_APP_PASSWORD env vars (set them in environment or in a local .env).")

client = MongoClient(MONGODB_URI)
db = client["email_llm"]
user_collection = db["patient"]
convo_collection = db["conversation"]

model = st("local_model")

loader = TextLoader("C:/Users/tushar.mehta/q/document.txt",encoding='utf-8')
documents = loader.load()

imap_server = 'imap.gmail.com'
email_user = GMAIL_ADDRESS
email_pass = GMAIL_APP_PASSWORD
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def read_email():
    mail=imaplib.IMAP4_SSL(imap_server)
    mail.login(email_user,email_pass)
    mail.select('inbox')

    status,messages=mail.search(None,"UNSEEN")
    mail_id=messages[0].split()
    if not mail_id:
        print("No new emails.")
        return None
    latest_email_id=mail_id[-1]
    status,data=mail.fetch(latest_email_id,'(RFC822)')
    raw_email=data[0][1]
    msg = email.message_from_bytes(raw_email)
    sender=msg['From']
    subject=msg['Subject']
    body=""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                body = part.get_payload(decode=True).decode()
                break
    else:
        body = msg.get_payload(decode=True).decode()
    print("Email received from:", sender)
    
    prompt = f"""
    Extract structured information from the email.
    Email Content:
    {body}
    Sender:
    {sender}

    Return ONLY JSON in this format:
    {{
        "name": "",
        "email": "",
        "reason": "",

    }}

    Rules:
    - name = person's name (if not found → "Unknown")
    - email = extract from sender
    - reason = why they are contacting (appointment, surgery, consultation, etc.)
    
    """

    response = ollama.chat(
        model='mistral',   # or qwen
        messages=[{"role": "user", "content": prompt}]
    )

    text = response['message']['content']

    try:
        data = json.loads(text)
    except:
        # fallback if LLM messes up JSON
        data = {
            "name": "Unknown",
            "email": sender,
            "reason": "general inquiry",
            "intent": "inquiry"
        }
    print("Extracted Data:", data)
    return {
    "sender": sender,
    "name": data['name'],
    "subject": subject,
    "reason": data['reason'],
    "body": body
    }   


import json
import re

def generate_res(name, email, reason, last_visit, user_input):

    prompt = f"""
    You are a professional email assistant.

    Name: {name}
    Email: {email}
    Reason: {reason}
    Last Visit: {last_visit}

    User Request:
    {user_input}

    Return ONLY JSON:
    {{
        "subject": "",
        "body": ""
    }}
    """

    response = ollama.chat(
        model='mistral',
        messages=[{"role": "user", "content": prompt}]
    )

    text = response['message']['content']

    try:
        data = json.loads(text)
    except:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        data = json.loads(match.group()) if match else {
            "subject": "Hospital Response",
            "body": text
        }

    return data["subject"], data["body"]

def write_email(name,email,reason,last_visit,user_input):
    save_data(name,email, reason)
    response = generate_res(name,email,reason,last_visit,user_input)
    print("Generated Email Response:", response)
    return response

def send_email(sender, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = email_user
    msg["To"] = sender

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(email_user, email_pass)

    server.send_message(msg)
    server.quit()

def save_data(name, email, reason, response):
    existing = user_collection.find_one({"email": email})

    if existing:
        user_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "name": name,
                    "reason": reason,
                    "response": response,
                    "last_visit": str(datetime.now())
                }
            }
        )
    else:
        user_collection.insert_one({
            "name": name,
            "email": email,
            "reason": reason,
            "response": response,
            "last_visit": str(datetime.now())
        })

def email_bot():
    email_data = read_email()

    if not email_data:
        return "No new email"

    sender = email_data["sender"]
    name = email_data["name"]
    reason = email_data["reason"]
    subject_in = email_data["subject"]
    body_in = email_data["body"]

    # fetch last visit
    user = user_collection.find_one({"email": sender})
    last_visit = user["last_visit"] if user else "First Visit"

    # generate response
    subject, body = generate_res(name, sender, reason, last_visit, body_in)

    # save user
    save_data(name, sender, reason, body)

    # send email
    send_email(sender, subject, body)

    print(" Email sent to:", sender)

    return "Email sent"


while True:
    a=email_bot()
    time.sleep(30) 
    