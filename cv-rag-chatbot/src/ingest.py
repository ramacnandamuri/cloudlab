try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from fastembed import TextEmbedding
from langchain_core.embeddings import Embeddings
from typing import List

# ── FastEmbed Wrapper ─────────────────────
class FastEmbedWrapper(Embeddings):
    def __init__(self, model_name: str):
        self.model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [
            [float(x) for x in embedding]
            for embedding in self.model.embed(texts)
        ]

    def embed_query(self, text: str) -> List[float]:
        embedding = list(self.model.embed([text]))[0]
        return [float(x) for x in embedding]

# ── Config ────────────────────────────────
DATA_DIR   = "data"
CHROMA_DIR = "chroma_db"

def load_documents():
    """Load all documents from data folder"""
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
    """Split documents into small chunks"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks")
    return chunks

def store_in_chromadb(chunks):
    """Convert chunks to vectors and store in ChromaDB"""
    print("Creating embeddings and storing in ChromaDB...")

    embeddings = FastEmbedWrapper(
        model_name="BAAI/bge-small-en-v1.5"
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