import faiss 
import ollama
import gradio as gr
from pymongo import MongoClient
import numpy as np
from datetime import datetime
import os
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer as st
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

load_dotenv()

MONGODB_URI = os.environ.get("MONGODB_URI")
if not MONGODB_URI:
    raise RuntimeError("Missing MONGODB_URI env var (set it in environment or in a local .env).")

client = MongoClient(MONGODB_URI)
db = client["email_llm"]
user_collection = db["patient"]
convo_collection = db["conversation"]
model = st("local_model")

loader = TextLoader("C:/Users/tushar.mehta/q/document.txt",encoding='utf-8')
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=500,  # Approximate chunk size in characters
                                               chunk_overlap=100 ) # Overlap helps preserve meaning across chunks)
chunks = text_splitter.split_documents(documents)

embed_model=st('all-MiniLM-L6-v2')

doc_embeddings = embed_model.encode(
    [doc.page_content for doc in chunks]
).astype('float32')
dim=doc_embeddings.shape[1]
index=faiss.IndexFlatL2(dim)
index.add(doc_embeddings)

def retrieve(query):
    q_emb = embed_model.encode([query])
    distances, indices = index.search(np.array(q_emb).astype('float32'), k=2)

    results = []
    for i in indices[0]:
        results.append(chunks[i].page_content)

    return results

def generate_res(name,email,reason,last_visit,user_input):
    context= retrieve(user_input)
    prompt=f"""
    you are an email assisant.
    name: {name}
    email: {email}
    reason: {reason}
    last visit: {last_visit}
    context: {context}
    task: {user_input}

    generate a professional email response based on the user request and context.
    subject should be "Welcome to our clinic"
    """
    response = ollama.chat(
        model='mistral',
        messages=[
                   {"role": "user", "content": prompt}]
    )
    return response['message']['content']


def save_data(name, email, reason):
    existing = user_collection.find_one({"email": email})

    if existing:
        user_collection.update_one(
            {"email": email},
            {
                "$set": {       
                    "name": name,
                    "reason": reason,
                    "last_visit": str(datetime.now())
                }
            }
        )
    else:
        user_collection.insert_one({
            "name": name,
            "email": email,
            "reason": reason,
            "last_visit": str(datetime.now())
        })
def save_chat(name,email,query, response):
    convo_collection.insert_one({
        "name": name,
        "email": email,
        "query": query,
        "response": response,
        "timestamp": str(datetime.now())
    })
def write_email(name,email,reason,last_visit,user_input):
    save_data(name,email, reason)
    response = generate_res(name,email,reason,last_visit,user_input)
    save_chat(name,email,user_input,response)
    return response
with gr.Blocks() as app:
    gr.Markdown("# Tushar Mehta Hospital Email Assistant")

    with gr.Row():
        name = gr.Textbox(label="Name")
        email = gr.Textbox(label="Email")

    with gr.Row():
        reason = gr.Textbox(label="Reason for Visit")
        last_visit = gr.Textbox(label="Last Visit (optional)")

    user_input = gr.Textbox(label="What email do you want to generate?")

    output = gr.Textbox(label="Generated Email", lines=15)

    btn = gr.Button("Generate Email")

    btn.click(
        write_email,
        inputs=[name, email, reason, last_visit, user_input],
        outputs=output
    )

app.launch()