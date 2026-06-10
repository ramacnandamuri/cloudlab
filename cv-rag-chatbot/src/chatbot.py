from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

# ── Config ────────────────────────────────
CHROMA_DIR  = "chroma_db"
EMBED_MODEL = "nomic-embed-text"
LLM_MODEL   = "llama3.2"

def load_vectorstore():
    """Load existing ChromaDB"""
    embeddings = OllamaEmbeddings(model=EMBED_MODEL)
    vectorstore = Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=embeddings
    )
    print("Loaded ChromaDB!")
    return vectorstore

def create_rag_chain(vectorstore):
    """Create modern RAG chain using LCEL"""

    # LLM
    llm = ChatOllama(model=LLM_MODEL)

    # Retriever — finds top 3 similar chunks
    retriever = vectorstore.as_retriever(
        search_kwargs={"k": 3}
    )

    # Prompt template
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

    # Helper to format retrieved chunks
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # Modern LCEL chain
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

def chat(chain):
    """Interactive chat loop"""
    print("\n" + "="*50)
    print("CV RAG Chatbot Ready!")
    print("Ask me anything about the candidate")
    print("Type 'quit' to exit")
    print("="*50 + "\n")

    while True:
        question = input("You: ").strip()

        if question.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not question:
            continue

        print("\nThinking...")
        answer = chain.invoke(question)
        print(f"\nBot: {answer}")
        print("\n" + "-"*40 + "\n")

if __name__ == "__main__":
    vectorstore = load_vectorstore()
    chain       = create_rag_chain(vectorstore)
    chat(chain)