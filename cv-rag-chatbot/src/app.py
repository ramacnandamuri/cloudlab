import os
import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

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

# ── Load RAG chain (cached) ───────────────
@st.cache_resource
def load_rag_chain():

    # HuggingFace embeddings — free, works everywhere!
    embeddings = HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2"
    )

    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 3}
    )

    # Groq LLM — free cloud LLM!
    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=os.getenv("GROQ_API_KEY")
    )

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

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough()
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

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
            chain  = load_rag_chain()
            answer = chain.invoke(question)
            st.markdown(answer)

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
        "What is the candidate's education?",
        "What DevOps tools do they know?",
    ]
    for q in questions:
        st.markdown(f"• {q}")

    st.divider()
    st.caption("Powered by LangChain + ChromaDB + Groq")
    st.caption("RAG — Retrieval Augmented Generation")
    st.caption("🔒 Running on secure cloud infrastructure")