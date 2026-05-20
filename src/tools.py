import random

def check_server_health(server_name: str) -> str:
    """Check if a server is healthy"""
    cpu = random.randint(60, 99)
    memory = random.randint(60, 99)
    return f"Server {server_name}: CPU {cpu}%, Memory {memory}%"

def restart_service(server_name: str) -> str:
    """Restart a failing service"""
    return f"Service on {server_name} restarted successfully ✅"