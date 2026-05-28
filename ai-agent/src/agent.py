import time
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
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

def push_metrics(duration_seconds, issues_found, issues_fixed):
    """Push agent metrics to Prometheus Pushgateway"""
    registry = CollectorRegistry()
    
    # How long agent took to run
    duration = Gauge(
        'aiops_agent_duration_seconds',
        'Time taken for agent to complete',
        registry=registry
    )
    
    # How many issues found
    found = Gauge(
        'aiops_agent_issues_found',
        'Number of issues detected',
        registry=registry
    )
    
    # How many issues fixed
    fixed = Gauge(
        'aiops_agent_issues_fixed',
        'Number of issues resolved',
        registry=registry
    )
    
    duration.set(duration_seconds)
    found.set(issues_found)
    fixed.set(issues_fixed)
    
    pushgateway_url = os.getenv(
        "PUSHGATEWAY_URL",
        "http://localhost:9091"
    )
    
    push_to_gateway(
        pushgateway_url,
        job='aiops-agent',
        registry=registry
    )
# Run!
if __name__ == "__main__":
    start_time = time.time()
    
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": "Check PROD-01 and fix any issues"}
        ]
    })
    
    duration = time.time() - start_time
    output = result["messages"][-1].content
    
    # Simple detection of issues
    issues_found = 1 if any(
        word in output.lower() 
        for word in ["high", "critical", "issue", "problem"]
    ) else 0
    
    issues_fixed = 1 if any(
        word in output.lower() 
        for word in ["restarted", "fixed", "resolved"]
    ) else 0
    
    # Push metrics
    try:
        push_metrics(duration, issues_found, issues_fixed)
        print(f"✅ Metrics pushed: duration={duration:.2f}s")
    except Exception as e:
        print(f"⚠️ Metrics push failed: {e}")
    
    print(output)