import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

# ── Config ────────────────────────────────
DATA_DIR    = "data"
CHROMA_DIR  = "chroma_db"
EMBED_MODEL = "nomic-embed-text"

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

    embeddings = OllamaEmbeddings(model=EMBED_MODEL)

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