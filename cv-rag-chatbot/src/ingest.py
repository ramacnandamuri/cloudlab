from dotenv import load_dotenv
load_dotenv()

import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# ── Config ────────────────────────────────
DATA_DIR   = "data"
CHROMA_DIR = "chroma_db"

def load_documents():
    docs = []
    for filename in os.listdir(DATA_DIR):
        filepath = os.path.join(DATA_DIR, filename)
        print(f"Loading: {filename}")
        if filename.endswith(".pdf"):
            loader = PyPDFLoader(filepath)
            docs.extend(loader.load())
        elif filename.endswith(".docx"):
            loader = Docx2txtLoader(filepath)
            docs.extend(loader.load())
    print(f"Loaded {len(docs)} document pages")
    return docs

def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")
    return chunks

def store_in_chromadb(chunks):
    print("Creating embeddings and storing in ChromaDB...")

    # HuggingFace embeddings — free, works everywhere!
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    print(f"Stored {len(chunks)} chunks in ChromaDB!")
    return vectorstore

if __name__ == "__main__":
    print("Starting CV ingestion...")
    docs   = load_documents()
    chunks = split_documents(docs)
    store_in_chromadb(chunks)
    print("Done! CV is ready to query.")