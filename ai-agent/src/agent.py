from langchain_ollama import OllamaLLM
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import tool
from langchain import hub
from src.prompts import SYSTEM_PROMPT
from src.tools import check_server_health, restart_service

# Step 1 - Connect to local Ollama LLM
llm = OllamaLLM(model="llama3.2")

# Step 2 - Define tools
@tool
def check_health(server_name: str) -> str:
    """Check server health. Input is server name."""
    return check_server_health(server_name)

@tool
def restart(server_name: str) -> str:
    """Restart a failing service. Input is server name."""
    return restart_service(server_name)

tools = [check_health, restart]

# Step 3 - Get ReAct prompt from LangChain hub
prompt = hub.pull("hwchase17/react")

# Step 4 - Create agent
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    handle_parsing_errors=True
)

# Step 5 - Give agent a goal!
if __name__ == "__main__":
    result = agent_executor.invoke({
        "input": f"{SYSTEM_PROMPT}\nCheck PROD-01 and fix any issues"
    })
    print(result["output"])