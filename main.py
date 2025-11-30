"""
Multi-Agent System Launcher
Orchestrates the startup of the supervisor and all registered worker agents.
Provides centralized environment validation and health monitoring.
"""

import os
import sys
import time
import asyncio
import subprocess
from typing import List, Dict, Optional
import yaml
import json


def validate_environment() -> bool:
    """
    Validate that all required environment variables and configurations exist.
    
    Returns:
        True if environment is valid, False otherwise
    """
    print("🔍 Validating environment...")
    
    # Check for required files
    required_files = [
        "config/settings.yaml",
        "config/registry.json",
        "requirements.txt"
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Missing required file: {file_path}")
            return False
    
    # Check Python version
    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return False
    
    print("✅ Environment validation passed")
    return True


def load_configuration() -> Dict:
    """
    Load system configuration from settings.yaml.
    
    Returns:
        Dictionary containing configuration
    """
    with open("config/settings.yaml", "r") as f:
        return yaml.safe_load(f)


def load_registry() -> List[Dict]:
    """
    Load agent registry from registry.json.
    
    Returns:
        List of registered agents
    """
    with open("config/registry.json", "r") as f:
        return json.load(f)


async def check_service_health(url: str, service_name: str, max_retries: int = 10) -> bool:
    """
    Check if a service is healthy by polling its health endpoint.
    
    Args:
        url: Base URL of the service
        service_name: Name of the service for logging
        max_retries: Maximum number of retry attempts
        
    Returns:
        True if service is healthy, False otherwise
    """
    import httpx
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/health", timeout=2.0)
                if response.status_code == 200:
                    print(f"✅ {service_name} is healthy")
                    return True
        except Exception:
            if attempt < max_retries - 1:
                print(f"⏳ Waiting for {service_name} (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(2)
            else:
                print(f"❌ {service_name} health check failed")
                return False
    
    return False


def start_supervisor(config: Dict) -> Optional[subprocess.Popen]:
    """
    Start the supervisor service.
    
    Args:
        config: System configuration dictionary
        
    Returns:
        Subprocess object or None if failed
    """
    supervisor_config = config.get("supervisor", {})
    host = supervisor_config.get("host", "127.0.0.1")
    port = supervisor_config.get("port", 8000)
    
    print(f"🚀 Starting Supervisor on {host}:{port}...")
    
    try:
        process = subprocess.Popen(
            ["uvicorn", "supervisor.main:app", "--host", host, "--port", str(port), "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return process
    except Exception as e:
        print(f"❌ Failed to start supervisor: {e}")
        return None


def start_worker(agent_config: Dict, system_config: Dict) -> Optional[subprocess.Popen]:
    """
    Start a worker agent service.
    
    Args:
        agent_config: Agent configuration from registry
        system_config: System configuration dictionary
        
    Returns:
        Subprocess object or None if failed
    """
    agent_id = agent_config.get("id")
    
    # Map agent ID to module path
    # For now, only gemini-wrapper is supported
    module_map = {
        "gemini-wrapper": "agents.gemini_wrapper.app:app"
    }
    
    module_path = module_map.get(agent_id)
    if not module_path:
        print(f"⚠️  No module mapping for agent: {agent_id}")
        return None
    
    # Extract port from URL (e.g., http://localhost:5010 -> 5010)
    url = agent_config.get("url", "")
    try:
        port = int(url.split(":")[-1])
    except (ValueError, IndexError):
        print(f"❌ Invalid URL format for {agent_id}: {url}")
        return None
    
    print(f"🚀 Starting {agent_config.get('name', agent_id)} on port {port}...")
    
    try:
        process = subprocess.Popen(
            ["uvicorn", module_path, "--host", "127.0.0.1", "--port", str(port), "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        return process
    except Exception as e:
        print(f"❌ Failed to start {agent_id}: {e}")
        return None


async def main():
    """Main orchestration function."""
    print("\n" + "="*60)
    print("🤖 Multi-Agent System Launcher")
    print("="*60 + "\n")
    
    # Validate environment
    if not validate_environment():
        print("\n❌ Environment validation failed. Exiting.")
        sys.exit(1)
    
    # Load configuration
    print("\n📋 Loading configuration...")
    config = load_configuration()
    registry = load_registry()
    print(f"✅ Loaded configuration for {len(registry)} registered agents")
    
    # Start services
    print("\n🚀 Starting services...\n")
    
    processes = []
    
    # Start supervisor
    supervisor_process = start_supervisor(config)
    if supervisor_process:
        processes.append(("Supervisor", supervisor_process))
        time.sleep(2)  # Give supervisor time to start
    
    # Start worker agents
    for agent in registry:
        worker_process = start_worker(agent, config)
        if worker_process:
            processes.append((agent.get("name", agent["id"]), worker_process))
            time.sleep(1)  # Stagger worker starts
    
    # Health checks
    print("\n🏥 Performing health checks...\n")
    
    supervisor_healthy = await check_service_health(
        f"http://{config['supervisor']['host']}:{config['supervisor']['port']}",
        "Supervisor"
    )
    
    workers_healthy = []
    for agent in registry:
        is_healthy = await check_service_health(agent["url"], agent["name"])
        workers_healthy.append(is_healthy)
    
    # Summary
    print("\n" + "="*60)
    print("📊 System Status")
    print("="*60)
    print(f"Supervisor: {'✅ Running' if supervisor_healthy else '❌ Failed'}")
    print(f"Workers: {sum(workers_healthy)}/{len(workers_healthy)} healthy")
    
    if supervisor_healthy and all(workers_healthy):
        print("\n✅ All services are running and healthy!")
        print("\n🌐 Access Points:")
        print(f"   Supervisor API: http://{config['supervisor']['host']}:{config['supervisor']['port']}/docs")
        for agent in registry:
            print(f"   {agent['name']}: {agent['url']}/docs")
        print("\n💡 Press CTRL+C to stop all services")
        
        try:
            # Keep processes running
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down services...")
            for name, process in processes:
                process.terminate()
                print(f"   Stopped {name}")
            print("✅ All services stopped")
    else:
        print("\n❌ Some services failed to start properly")
        print("Please check the logs and try again")
        for name, process in processes:
            process.terminate()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
