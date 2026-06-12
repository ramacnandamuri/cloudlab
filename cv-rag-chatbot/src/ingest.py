try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

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
    """Store chunks in ChromaDB using default embeddings"""
    print("Storing in ChromaDB...")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef = DefaultEmbeddingFunction()

    # Delete existing collection if exists
    try:
        client.delete_collection("cv_chunks")
    except:
        pass

    collection = client.get_or_create_collection(
        name="cv_chunks",
        embedding_function=ef
    )

    texts = [chunk.page_content for chunk in chunks]
    ids   = [str(i) for i in range(len(chunks))]

    collection.add(documents=texts, ids=ids)
    print(f"Stored {len(chunks)} chunks in ChromaDB!")

if __name__ == "__main__":
    print("Starting CV ingestion...")
    docs   = load_documents()
    chunks = split_documents(docs)
    store_in_chromadb(chunks)
    print("Done! CV is ready to query.")