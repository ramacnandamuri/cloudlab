import os
import streamlit as st
import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# ── Load .env ─────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Config ────────────────────────────────
CHROMA_DIR = "chroma_db"

# ── Page Setup ────────────────────────────
st.set_page_config(
    page_title="CV Assistant",
    page_icon="🤖",
    layout="centered"
)

# ── Header ────────────────────────────────
st.title("🤖 CV Assistant")
st.markdown("**Ask me anything about the candidate's experience, skills, and projects.**")
st.divider()

# ── Load components (cached) ──────────────
@st.cache_resource
def load_components():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    ef = DefaultEmbeddingFunction()
    collection = client.get_collection(
        name="cv_chunks",
        embedding_function=ef
    )
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )
    return collection, llm

def get_answer(question, collection, llm):
    """Search CV and generate answer"""
    # Search ChromaDB for relevant chunks
    results = collection.query(
        query_texts=[question],
        n_results=3
    )
    context = "\n\n".join(results["documents"][0])

    # Build prompt
    prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant answering questions
about a candidate's CV and experience.

Use ONLY the context below to answer.
If the answer is not in the context say:
"I don't have that information in the CV."

Context:
{context}

Question: {question}

Answer:""")

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({
        "context": context,
        "question": question
    })

# ── Chat History ──────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "Hi! I'm the CV Assistant. Ask me anything about the candidate's skills, experience, or projects! 😊"
        }
    ]

# ── Display Chat History ──────────────────
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ── Chat Input ────────────────────────────
if question := st.chat_input("Ask about the candidate..."):
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching CV..."):
            collection, llm = load_components()
            answer = get_answer(question, collection, llm)
            st.markdown(answer)

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

# ── Sidebar ───────────────────────────────
with st.sidebar:
    st.header("💡 Try asking:")
    questions = [
        "What AWS services has the candidate used?",
        "What projects have they built?",
        "How much experience do they have?",
        "What is their education background?",
        "What AI skills do they have?",
        "Why should I hire this candidate?",
        "What CI/CD tools have they used?",
        "Are they available immediately?",
    ]
    for q in questions:
        st.markdown(f"• {q}")

    st.divider()
    st.caption("Powered by ChromaDB + Groq + LangChain")
    st.caption("RAG — Retrieval Augmented Generation")
    st.caption("🔒 Running on secure cloud infrastructure")