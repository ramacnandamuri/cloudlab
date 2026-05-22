import os
from langchain_aws import ChatBedrock
from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from src.prompts import SYSTEM_PROMPT
from src.tools import check_server_health, restart_service

# Switch between local and production!
ENV = os.getenv("AGENT_ENV", "local")

if ENV == "production":
    # Production = AWS Bedrock
    llm = ChatBedrock(
    model_id="amazon.nova-lite-v1:0",
        region_name="eu-west-2"
    )
else:
    # Local = Ollama (free!)
    llm = ChatOllama(
        model="llama3.2",
        base_url=os.getenv(
            "OLLAMA_URL",
            "http://localhost:11434"
        )
    )

# Define tools
@tool
def check_health(server_name: str) -> str:
    """Check server health. Input is server name."""
    return check_server_health(server_name)

@tool
def restart(server_name: str) -> str:
    """Restart a failing service. Input is server name."""
    return restart_service(server_name)

tools = [check_health, restart]

# Create agent using LangGraph
agent = create_react_agent(
    model=llm,
    tools=tools,
    prompt=SYSTEM_PROMPT
)

# Run!
if __name__ == "__main__":
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": "Check PROD-01 and fix any issues"}
        ]
    })
    # Print final response
    print(result["messages"][-1].content)