import os
import json
import streamlit as st
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
import os
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHUNKS_FILE = os.path.join(BASE_DIR, "data", "cv_chunks.json")

# ── Page Setup ────────────────────────────
st.set_page_config(
    page_title="CV Assistant",
    page_icon="🤖",
    layout="centered"
)

st.title("🤖 CV Assistant")
st.markdown("**Ask me anything about the candidate's experience, skills, and projects.**")
st.divider()

# ── Load LLM (cached) ─────────────────────
@st.cache_resource
def load_llm():
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

# ── Load CV chunks (cached) ───────────────
@st.cache_data
def load_chunks():
    with open(CHUNKS_FILE, "r") as f:
        return json.load(f)

def get_answer(question, chunks, llm):
    """Simple keyword search + LLM answer"""
    question_lower = question.lower()
    words = question_lower.split()

    # Score each chunk by keyword matches
    scored = []
    for chunk in chunks:
        score = sum(
            1 for word in words
            if word in chunk.lower() and len(word) > 3
        )
        scored.append((score, chunk))

    # Get top 3 most relevant chunks
    scored.sort(reverse=True)
    context = "\n\n".join([c for _, c in scored[:3]])

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
            llm    = load_llm()
            chunks = load_chunks()
            answer = get_answer(question, chunks, llm)
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
    st.caption("Powered by Groq + LangChain")
    st.caption("RAG — Retrieval Augmented Generation")