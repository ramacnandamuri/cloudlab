try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os
import json
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR    = "data"
CHUNKS_FILE = "data/cv_chunks.json"

def load_documents():
    docs = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith(('.pdf', '.docx')):
            filepath = os.path.join(DATA_DIR, filename)
            print(f"Loading: {filename}")
            if filename.endswith(".pdf"):
                loader = PyPDFLoader(filepath)
            else:
                loader = Docx2txtLoader(filepath)
            docs.extend(loader.load())
    print(f"Loaded {len(docs)} pages")
    return docs

def split_and_save(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_documents(docs)
    texts  = [chunk.page_content for chunk in chunks]

    with open(CHUNKS_FILE, "w") as f:
        json.dump(texts, f)

    print(f"Saved {len(texts)} chunks to {CHUNKS_FILE}")

if __name__ == "__main__":
    docs = load_documents()
    split_and_save(docs)
    print("Done!")