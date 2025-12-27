#!/usr/bin/env python3
"""
Backend Startup Script for Chatbot-UIT
======================================
Khoi dong toan bo backend services:
- Docker services (OpenSearch, Weaviate, Neo4j)
- RAG Service (port 8000)
- Orchestrator Service (port 8001)

Neu cac dich vu dang chay, script se tu dong stop truoc khi khoi dong lai.

Usage:
    python start_backend.py                # Khoi dong tat ca services
    python start_backend.py --skip-docker  # Bo qua Docker services
    python start_backend.py --stop         # Chi stop tat ca services
"""

import subprocess
import sys
import time
import signal
import os
import argparse
from pathlib import Path
from typing import List, Optional


class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    NC = '\033[0m'
    BOLD = '\033[1m'


processes: List[subprocess.Popen] = []


def print_header(text: str):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.NC}")
    print(f"{Colors.BOLD}{text.center(70)}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*70}{Colors.NC}\n")


def print_success(text: str):
    print(f"{Colors.GREEN}✓ {text}{Colors.NC}")


def print_error(text: str):
    print(f"{Colors.RED}✗ {text}{Colors.NC}")


def print_info(text: str):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.NC}")


def print_step(step: int, total: int, text: str):
    print(f"\n{Colors.BOLD}[{step}/{total}] {text}{Colors.NC}")


def run_command(cmd: List[str], cwd: Optional[Path] = None, check: bool = True) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check)
        return result
    except subprocess.CalledProcessError as e:
        return e


def check_port(port: int) -> bool:
    result = run_command(["lsof", "-Pi", f":{port}", "-sTCP:LISTEN", "-t"], check=False)
    return result.returncode == 0


def kill_port(port: int):
    if check_port(port):
        print_info(f"Stopping process on port {port}...")
        run_command(["bash", "-c", f"lsof -ti:{port} | xargs kill -9 2>/dev/null || true"], check=False)
        time.sleep(1)


def check_docker() -> bool:
    result = run_command(["docker", "ps"], check=False)
    return result.returncode == 0


def detect_docker_compose_command() -> Optional[List[str]]:
    """Detect which docker compose command is available (v2 plugin or v1 standalone)"""
    # Try docker compose (v2 plugin) first
    result = run_command(["docker", "compose", "version"], check=False)
    if result.returncode == 0:
        print_info("Using 'docker compose' (v2 plugin)")
        return ["docker", "compose"]
    
    # Try docker-compose (v1 standalone)
    result = run_command(["docker-compose", "version"], check=False)
    if result.returncode == 0:
        print_info("Using 'docker-compose' (v1 standalone)")
        return ["docker-compose"]
    
    return None


def get_project_root() -> Path:
    return Path(__file__).parent.parent.absolute()


def stop_all_services(project_root: Path, skip_docker: bool = False):
    print_header("🛑 STOPPING ALL SERVICES")
    
    print_info("Stopping Python services...")
    kill_port(8000)
    kill_port(8001)
    
    if not skip_docker:
        print_info("Stopping Docker services...")
        infra_dir = project_root / "infrastructure"
        
        docker_compose_cmd = detect_docker_compose_command()
        
        if infra_dir.exists() and docker_compose_cmd:
            for compose_file in ["docker-compose.neo4j.yml", "docker-compose.opensearch.yml", "docker-compose.weaviate.yml"]:
                compose_path = infra_dir / compose_file
                if compose_path.exists():
                    cmd = docker_compose_cmd + ["-f", compose_file, "down"]
                    run_command(cmd, cwd=infra_dir, check=False)
            
            main_compose = infra_dir / "docker-compose.yml"
            if main_compose.exists():
                cmd = docker_compose_cmd + ["down"]
                run_command(cmd, cwd=infra_dir, check=False)
        
        time.sleep(2)
    
    print_success("All services stopped!")


def start_docker_services(project_root: Path):
    print_step(1, 3, "Starting Docker Services")
    
    if not check_docker():
        print_error("Docker is not running!")
        print_info("Please start Docker Desktop or Docker daemon first")
        sys.exit(1)
    
    infra_dir = project_root / "infrastructure"
    
    if not infra_dir.exists():
        print_error(f"Infrastructure directory not found: {infra_dir}")
        sys.exit(1)
    
    # Detect docker compose command (v2 uses "docker compose", v1 uses "docker-compose")
    docker_compose_cmd = detect_docker_compose_command()
    if not docker_compose_cmd:
        print_error("Neither 'docker compose' nor 'docker-compose' is available!")
        sys.exit(1)
    
    compose_files = [
        "docker-compose.opensearch.yml",
        "docker-compose.weaviate.yml", 
        "docker-compose.neo4j.yml"
    ]
    
    print_info("Starting OpenSearch, Weaviate, and Neo4j...")
    
    for compose_file in compose_files:
        compose_path = infra_dir / compose_file
        if compose_path.exists():
            cmd = docker_compose_cmd + ["-f", compose_file, "up", "-d"]
            result = run_command(cmd, cwd=infra_dir, check=False)
            if result.returncode != 0:
                print_error(f"Failed to start {compose_file}")
                if hasattr(result, 'stderr') and result.stderr:
                    print_error(f"  Error: {result.stderr.strip()}")
                if hasattr(result, 'stdout') and result.stdout:
                    print_info(f"  Output: {result.stdout.strip()}")
        else:
            print_error(f"Compose file not found: {compose_path}")
    
    print_info("Waiting for services to be ready...")
    max_retries = 30
    
    for i in range(max_retries):
        opensearch_ok = run_command(
            ["curl", "-sf", "http://localhost:9200/_cluster/health"],
            check=False
        ).returncode == 0
        
        weaviate_ok = run_command(
            ["curl", "-sf", "http://localhost:8090/v1/.well-known/ready"],
            check=False
        ).returncode == 0
        
        neo4j_ok = run_command(
            ["curl", "-sf", "http://localhost:7474"],
            check=False
        ).returncode == 0
        
        if opensearch_ok and weaviate_ok and neo4j_ok:
            print()
            print_success("All Docker services are healthy!")
            print_info("  - OpenSearch: http://localhost:9200")
            print_info("  - Weaviate: http://localhost:8090")
            print_info("  - Neo4j: http://localhost:7474 (bolt://localhost:7687)")
            return
        
        print(".", end="", flush=True)
        time.sleep(2)
    
    print()
    print_error("Some Docker services may not be healthy yet")
    print_info("Continuing anyway... Services might still be starting")


def start_rag_service(project_root: Path):
    print_step(2, 3, "Starting RAG Service (port 8000)")
    
    rag_dir = project_root / "services" / "rag_services"
    
    if not rag_dir.exists():
        print_error(f"RAG services directory not found: {rag_dir}")
        return None
    
    env_file = rag_dir / ".env"
    if not env_file.exists():
        env_example = rag_dir / ".env.example"
        if env_example.exists():
            print_info("Creating .env from .env.example for RAG service...")
            import shutil
            shutil.copy(env_example, env_file)
    
    print_info(f"Starting RAG service from: {rag_dir}")
    
    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8000",
            "--reload"
        ],
        cwd=rag_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    processes.append(process)
    
    print_info("Waiting for RAG service to start...")
    output_lines = []
    for i in range(30):
        # Try to read any available output (non-blocking)
        try:
            import select
            if process.stdout and select.select([process.stdout], [], [], 0)[0]:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line)
        except:
            pass
        
        # Check if process has crashed
        if process.poll() is not None:
            print()
            print_error("RAG Service process crashed!")
            # Read remaining output
            if process.stdout:
                remaining = process.stdout.read()
                if remaining:
                    output_lines.append(remaining)
            if output_lines:
                print_error("Error output:")
                print(''.join(output_lines)[-2000:])
            return None
        
        if check_port(8000):
            print()
            print_success("RAG Service started successfully!")
            print_info("  - API: http://localhost:8000")
            print_info("  - Docs: http://localhost:8000/docs")
            return process
        time.sleep(1)
        print(".", end="", flush=True)
    
    print()
    print_error("RAG Service failed to start (timeout)")
    # Show collected output
    if output_lines:
        print_error("Service output:")
        print(''.join(output_lines)[-2000:])
    return None


def start_orchestrator_service(project_root: Path):
    print_step(3, 3, "Starting Orchestrator Service (port 8001)")
    
    orchestrator_dir = project_root / "services" / "orchestrator"
    
    if not orchestrator_dir.exists():
        print_error(f"Orchestrator directory not found: {orchestrator_dir}")
        return None
    
    env_file = orchestrator_dir / ".env"
    if not env_file.exists():
        env_example = orchestrator_dir / ".env.example"
        if env_example.exists():
            print_info("Creating .env from .env.example for Orchestrator...")
            import shutil
            shutil.copy(env_example, env_file)
        else:
            print_error("No .env file found for Orchestrator!")
            print_info("Please create .env file with OPENROUTER_API_KEY")
            return None
    
    env = os.environ.copy()
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    
    rag_services_path = str(project_root / "services" / "rag_services")
    existing_pythonpath = env.get('PYTHONPATH', '')
    if existing_pythonpath:
        env['PYTHONPATH'] = f"{orchestrator_dir}:{rag_services_path}:{existing_pythonpath}"
    else:
        env['PYTHONPATH'] = f"{orchestrator_dir}:{rag_services_path}"
    
    print_info(f"Starting Orchestrator service from: {orchestrator_dir}")
    
    process = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn",
            "app.main:app",
            "--host", "0.0.0.0",
            "--port", "8001",
            "--reload"
        ],
        cwd=orchestrator_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    
    processes.append(process)
    
    print_info("Waiting for Orchestrator service to start...")
    for i in range(30):
        # Check if process has crashed
        if process.poll() is not None:
            print()
            print_error("Orchestrator Service process crashed!")
            if process.stdout:
                output = process.stdout.read()
                if output:
                    print_error("Error output:")
                    print(output[-1500:])
            return None
        
        if check_port(8001):
            print()
            print_success("Orchestrator Service started successfully!")
            print_info("  - API: http://localhost:8001")
            print_info("  - Docs: http://localhost:8001/docs")
            return process
        time.sleep(1)
        print(".", end="", flush=True)
    
    print()
    print_error("Orchestrator Service failed to start (timeout)")
    if process.stdout:
        output = process.stdout.read()
        if output:
            print_error("Service output:")
            print(output[-1500:])
    return None


def signal_handler(sig, frame):
    print("\n")
    print_header("🛑 STOPPING BACKEND SERVICES")
    
    # Terminate Python service processes
    print_info("Stopping Python services...")
    for process in processes:
        try:
            process.terminate()
            process.wait(timeout=5)
            print_success(f"Process {process.pid} terminated")
        except subprocess.TimeoutExpired:
            print_info(f"Force killing process {process.pid}...")
            process.kill()
            process.wait()
        except Exception as e:
            print_error(f"Error stopping process: {e}")
    
    # Also kill any remaining processes on the ports
    kill_port(8000)
    kill_port(8001)
    
    print_success("All backend services stopped!")
    sys.exit(0)


def print_summary():
    print_header("🎉 BACKEND SERVICES STARTED")
    print(f"{Colors.GREEN}Services running:{Colors.NC}")
    print(f"  • OpenSearch:   http://localhost:9200")
    print(f"  • Weaviate:     http://localhost:8090")
    print(f"  • Neo4j:        http://localhost:7474 (bolt: 7687)")
    print(f"  • RAG Service:  http://localhost:8000/docs")
    print(f"  • Orchestrator: http://localhost:8001/docs")
    print()
    print(f"{Colors.BOLD}Database Credentials:{Colors.NC}")
    print(f"  • Neo4j: neo4j / uitchatbot")
    print()
    print(f"{Colors.YELLOW}Press Ctrl+C to stop all services{Colors.NC}")


def main():
    parser = argparse.ArgumentParser(description="Start/Stop Chatbot-UIT Backend Services")
    parser.add_argument("--skip-docker", action="store_true", help="Skip Docker services")
    parser.add_argument("--stop", action="store_true", help="Only stop services")
    args = parser.parse_args()
    
    project_root = get_project_root()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    stop_all_services(project_root, skip_docker=args.skip_docker)
    
    if args.stop:
        return
    
    print_header("🚀 STARTING CHATBOT-UIT BACKEND")
    
    print_info(f"Project root: {project_root}")
    print_info(f"Python: {sys.executable}")
    
    if not args.skip_docker:
        start_docker_services(project_root)
    else:
        print_step(1, 3, "Skipping Docker Services (--skip-docker)")
        print_info("Docker services skipped")
    
    rag_process = start_rag_service(project_root)
    if not rag_process:
        print_error("Failed to start RAG service!")
        sys.exit(1)
    
    orchestrator_process = start_orchestrator_service(project_root)
    if not orchestrator_process:
        print_error("Failed to start Orchestrator service!")
        sys.exit(1)
    
    print_summary()
    
    try:
        while True:
            for process in processes:
                if process.poll() is not None:
                    print_error("A service has stopped unexpectedly!")
                    if process.stdout:
                        output = process.stdout.read()
                        if output:
                            print(f"Output: {output[-2000:]}")
                    sys.exit(1)
            time.sleep(5)
    except KeyboardInterrupt:
        signal_handler(None, None)


if __name__ == "__main__":
    main()
