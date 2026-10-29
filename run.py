#!/usr/bin/env python3
"""
FEAS 2.0 - Universal Cross-Platform Launcher & Orchestrator
=============================================================
Runs seamlessly across Windows, macOS (Intel & Apple Silicon), Linux, and Docker.

Usage:
    python run.py [command] [options]

Commands:
    all           Run all core services (API + Workstation + Investigator)
    feas          Run FEAS Forensic Workstation & FastAPI Backend
    api           Run FEAS FastAPI Backend (Port 8000)
    workstation   Run FEAS Forensic Workstation UI (Port 8501)
    investigator  Run Deep Learning Forensic Investigator UI (Port 8502)
    frontend      Run Forensic 3D React Dashboard
    test          Run comprehensive test suite across all modules (94+ tests)
    doctor        Inspect platform, hardware acceleration, and dependencies
    setup         Initialize virtualenv and install dependencies for this platform
    docker        Launch via Docker Compose
"""

from __future__ import annotations

import argparse
import os
import platform
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent

# Ensure cross-platform UTF-8 output encoding
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ANSI Color formatting
IS_WIN_ANSI = sys.platform == "win32" and (
    os.environ.get("WT_SESSION") is not None
    or os.environ.get("TERM_PROGRAM") is not None
    or os.environ.get("ANSICON") is not None
    or "TERM" in os.environ
)

if IS_WIN_ANSI or sys.platform != "win32":
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"
    DIM = "\033[2m"
else:
    BOLD = GREEN = CYAN = YELLOW = RED = RESET = DIM = ""


def get_platform_info() -> Dict[str, str]:
    """Detect OS, CPU architecture, and execution details."""
    system = platform.system()
    arch = platform.machine()
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    
    os_name = {
        "Windows": "Microsoft Windows",
        "Darwin": "Apple macOS",
        "Linux": "Linux",
    }.get(system, system)
    
    return {
        "system": system,
        "os_name": os_name,
        "architecture": arch,
        "python_version": py_ver,
        "python_path": sys.executable,
        "in_venv": "Yes" if sys.prefix != sys.base_prefix else "No",
    }


def get_acceleration_info() -> Tuple[str, str]:
    """Detect GPU / acceleration hardware (CUDA, Apple MPS, or CPU)."""
    try:
        import torch
        if torch.cuda.is_available():
            dev_name = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "CUDA"
            return ("cuda", f"NVIDIA CUDA Acceleration ({dev_name})")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return ("mps", "Apple Metal Performance Shaders (MPS - Apple Silicon GPU)")
        return ("cpu", f"CPU Processing ({os.cpu_count() or 1} logical cores)")
    except ImportError:
        return ("cpu", "CPU Processing (PyTorch not yet imported)")


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a network port is already open/in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def check_tool_available(tool_cmd: str) -> bool:
    """Check whether an external tool (ffmpeg, docker, npm) is on PATH."""
    from shutil import which
    return which(tool_cmd) is not None


def print_banner():
    plat = get_platform_info()
    dev_type, dev_desc = get_acceleration_info()
    print(f"""
{CYAN}{BOLD}======================================================================
  FEAS 2.0 & Deep Learning Forensic Investigator
  Universal Cross-Platform Suite
======================================================================{RESET}
  {BOLD}Operating System :{RESET} {plat['os_name']} ({plat['architecture']})
  {BOLD}Python Version   :{RESET} {plat['python_version']} (Venv: {plat['in_venv']})
  {BOLD}Compute Device   :{RESET} {GREEN}{dev_desc}{RESET}
  {BOLD}Workspace Path   :{RESET} {ROOT_DIR}
----------------------------------------------------------------------""")


def run_doctor():
    """Perform health and platform readiness diagnostic."""
    print_banner()
    print(f"\n{BOLD}[1/4] Checking Essential Platform Tools...{RESET}")
    for tool, desc in [
        ("ffmpeg", "Video decoding, audio slicing, and transcode support"),
        ("git", "Version control and model weights management"),
        ("docker", "Containerized deployment (optional)"),
        ("node", "React 3D Dashboard dev server (optional)"),
    ]:
        avail = check_tool_available(tool)
        status = f"{GREEN}Available{RESET}" if avail else f"{YELLOW}Not found (optional/fallback active){RESET}"
        print(f"  - {tool:<8} : {status} - {desc}")

    print(f"\n{BOLD}[2/4] Checking Python Dependencies...{RESET}")
    modules_to_test = [
        ("torch", "PyTorch Deep Learning Engine"),
        ("torchvision", "Computer Vision Pretrained Models"),
        ("ultralytics", "YOLOv8 Real-Time CCTV Tracking"),
        ("cv2", "OpenCV Image & Video Processing"),
        ("fastapi", "High-throughput REST API"),
        ("uvicorn", "ASGI Production Server"),
        ("streamlit", "Interactive Forensic UI Engine"),
        ("reportlab", "Court-Admissible PDF Technical Reports"),
        ("PIL", "Pillow Image Processing"),
        ("aiosqlite", "Asynchronous SQLite Audit Trail"),
        ("firebase_admin", "Firebase Cloud Forensic Vault & Auth"),
    ]
    all_ok = True
    for mod_name, desc in modules_to_test:
        try:
            __import__(mod_name)
            print(f"  - {mod_name:<12} : {GREEN}OK{RESET} ({desc})")
        except ImportError:
            print(f"  - {mod_name:<12} : {RED}MISSING{RESET} ({desc})")
            all_ok = False

    print(f"\n{BOLD}[3/4] Checking Port Availability...{RESET}")
    ports = [
        (8000, "FastAPI REST Engine"),
        (8501, "FEAS Forensic Workstation UI"),
        (8502, "Deep Learning Investigator UI"),
        (5173, "React 3D Dashboard Dev Server"),
    ]
    for port, name in ports:
        in_use = is_port_in_use(port)
        status = f"{YELLOW}In Use (Occupied){RESET}" if in_use else f"{GREEN}Available{RESET}"
        print(f"  - Port {port:<5} : {status} [{name}]")

    print(f"\n{BOLD}[4/4] Hardware & Acceleration Audit...{RESET}")
    dev_type, dev_desc = get_acceleration_info()
    print(f"  - Primary Acceleration Device : {CYAN}{dev_desc}{RESET}")
    if dev_type == "cuda":
        print(f"  - {GREEN}Ready for GPU-accelerated YOLOv8 tracking and forensic inference.{RESET}")
    elif dev_type == "mps":
        print(f"  - {GREEN}Ready for Apple Silicon Metal MPS hardware acceleration.{RESET}")
    else:
        print(f"  - {CYAN}Running on CPU. All forensic algorithms operate with full accuracy and fallbacks.{RESET}")

    if all_ok:
        print(f"\n{GREEN}{BOLD}[OK] System Diagnosis: Fully ready to run across all platforms!{RESET}\n")
    else:
        print(f"\n{YELLOW}{BOLD}[!] System Diagnosis: Some packages missing. Run 'python run.py setup' to install.{RESET}\n")


def run_setup():
    """Install or sync dependencies across Windows, Linux, and macOS."""
    print_banner()
    print(f"{CYAN}Installing dependencies from requirements.txt...{RESET}")
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "pip"]
    subprocess.run(cmd)

    req_file = ROOT_DIR / "requirements.txt"
    if req_file.exists():
        cmd = [sys.executable, "-m", "pip", "install", "-r", str(req_file)]
        res = subprocess.run(cmd)
        if res.returncode == 0:
            print(f"\n{GREEN}{BOLD}✓ Successfully installed all requirements for {platform.system()}!{RESET}\n")
        else:
            print(f"\n{RED}Error installing requirements. Exit code: {res.returncode}{RESET}\n")
    else:
        print(f"{RED}requirements.txt not found at {req_file}{RESET}")


def run_tests():
    """Run all test suites across the entire repository."""
    print_banner()
    print(f"{CYAN}{BOLD}Running Automated Tests across all modules...{RESET}\n")

    suites = [
        ("Core Forensic Engine (tests/)", ROOT_DIR, ["tests"]),
        ("FEAS Forensic Suite (FEAS/tests/)", ROOT_DIR / "FEAS", ["tests"]),
        ("CCTV Pipeline Suite (deep_learning_forensic_investigator/tests/)", ROOT_DIR / "deep_learning_forensic_investigator", ["tests"]),
    ]

    total_failed = 0
    for name, cwd, test_dirs in suites:
        print(f"{BOLD}--> Executing {name}...{RESET}")
        env = os.environ.copy()
        # Set PYTHONPATH to include local folder to avoid cross-module shadowing
        curr_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(cwd) + (os.pathsep + curr_pp if curr_pp else "")

        cmd = [sys.executable, "-m", "pytest"] + test_dirs + ["-v", "--tb=short"]
        res = subprocess.run(cmd, cwd=str(cwd), env=env)
        if res.returncode != 0:
            print(f"{RED}Failed: {name}{RESET}\n")
            total_failed += 1
        else:
            print(f"{GREEN}Passed: {name}{RESET}\n")

    if total_failed == 0:
        print(f"{GREEN}{BOLD}[OK] All test suites passed successfully! (94+ Tests Verified){RESET}\n")
    else:
        print(f"{RED}{BOLD}[X] {total_failed} test suite(s) reported failures.{RESET}\n")


def launch_process(
    cmd: List[str],
    cwd: Path,
    name: str,
    extra_env: Optional[Dict[str, str]] = None,
) -> subprocess.Popen:
    """Launch a background process cleanly with environment and logging."""
    env = os.environ.copy()
    curr_pp = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(cwd) + (os.pathsep + curr_pp if curr_pp else "")
    if extra_env:
        env.update(extra_env)

    print(f"  {CYAN}▸ Starting {name}...{RESET}")
    print(f"    {DIM}Command : {' '.join(cmd)}{RESET}")
    print(f"    {DIM}Cwd     : {cwd}{RESET}")

    actual_cmd = list(cmd)
    if sys.platform == "win32" and actual_cmd and actual_cmd[0] == "npm":
        actual_cmd[0] = "npm.cmd"

    proc = subprocess.Popen(
        actual_cmd,
        cwd=str(cwd),
        env=env,
    )
    return proc


def terminate_processes(processes: List[Tuple[str, subprocess.Popen]]):
    """Cleanly terminate all spawned child processes cross-platform."""
    print(f"\n{YELLOW}Stopping services cleanly...{RESET}")
    for name, proc in processes:
        if proc.poll() is None:
            try:
                if sys.platform == "win32":
                    # On Windows, kill process tree
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    proc.terminate()
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
    print(f"{GREEN}All services shut down gracefully.{RESET}\n")


def run_services(targets: List[str]):
    """Launch requested services and monitor until Ctrl+C."""
    print_banner()

    processes: List[Tuple[str, subprocess.Popen]] = []

    try:
        # 1. FastAPI REST Backend
        if "api" in targets or "all" in targets or "feas" in targets:
            api_cwd = ROOT_DIR / "FEAS"
            api_port = os.environ.get("PORT", "8000")
            cmd = [
                sys.executable,
                "-m",
                "uvicorn",
                "src.main:app",
                "--host",
                "0.0.0.0",
                "--port",
                str(api_port),
            ]
            processes.append((f"FEAS FastAPI Backend (Port {api_port})", launch_process(cmd, api_cwd, "FEAS FastAPI Backend")))

        # 2. FEAS Forensic Workstation UI (Streamlit)
        if "workstation" in targets or "all" in targets or "feas" in targets:
            ui_cwd = ROOT_DIR / "FEAS"
            cmd = [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "src/ui/app.py",
                "--server.port",
                "8501",
                "--server.address",
                "0.0.0.0",
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ]
            processes.append(("FEAS Workstation UI (Port 8501)", launch_process(cmd, ui_cwd, "FEAS Workstation UI")))

        # 3. Deep Learning Forensic Investigator UI (Streamlit)
        if "investigator" in targets or "all" in targets:
            inv_cwd = ROOT_DIR / "deep_learning_forensic_investigator"
            cmd = [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "app.py",
                "--server.port",
                "8502",
                "--server.address",
                "0.0.0.0",
                "--server.headless",
                "true",
                "--browser.gatherUsageStats",
                "false",
            ]
            processes.append(("Deep Learning Investigator (Port 8502)", launch_process(cmd, inv_cwd, "Investigator UI")))

        # 4. React 3D Dashboard
        if "frontend" in targets or "all" in targets:
            fe_dir = ROOT_DIR / "FEAS" / "frontend"
            if check_tool_available("npm"):
                cmd = ["npm", "run", "dev"]
                processes.append(("React 3D Dashboard", launch_process(cmd, fe_dir, "React 3D Dashboard")))
            else:
                print(f"{YELLOW}npm is not installed. Access dashboard via http://localhost:8000/dashboard instead.{RESET}")

        print(f"\n{GREEN}{BOLD}Services are active:{RESET}")
        if any(t in targets for t in ["api", "all", "feas"]):
            print(f"  • {BOLD}FEAS REST API Docs   :{RESET} {CYAN}http://localhost:8000/docs{RESET}")
            print(f"  • {BOLD}FEAS Web Dashboard   :{RESET} {CYAN}http://localhost:8000/dashboard{RESET}")
        if any(t in targets for t in ["workstation", "all", "feas"]):
            print(f"  • {BOLD}FEAS Workstation UI  :{RESET} {CYAN}http://localhost:8501{RESET}")
        if any(t in targets for t in ["investigator", "all"]):
            print(f"  • {BOLD}Investigator UI      :{RESET} {CYAN}http://localhost:8502{RESET}")
        if any(t in targets for t in ["frontend", "all"]):
            print(f"  • {BOLD}React 3D Lab (Vite)  :{RESET} {CYAN}http://localhost:5174{RESET}")
        print(f"\n{BOLD}Press Ctrl+C to terminate all services.{RESET}\n")

        while True:
            # Check if any process died unexpectedly
            for name, proc in processes:
                code = proc.poll()
                if code is not None and code != 0:
                    print(f"\n{YELLOW}! Process '{name}' exited with code {code}.{RESET}")
            time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        terminate_processes(processes)


def run_docker():
    """Launch containerized setup via Docker Compose."""
    print_banner()
    if not check_tool_available("docker"):
        print(f"{RED}Error: Docker is not installed or not in PATH.{RESET}")
        print("Please install Docker Desktop (Windows/macOS) or Docker Engine (Linux).")
        return

    print(f"{CYAN}Launching FEAS 2.0 via Docker Compose...{RESET}\n")
    compose_file = ROOT_DIR / "docker-compose.yml"
    cmd = ["docker", "compose", "-f", str(compose_file), "up", "--build"]
    try:
        subprocess.run(cmd, cwd=str(ROOT_DIR))
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Stopping containers...{RESET}")
        subprocess.run(["docker", "compose", "-f", str(compose_file), "down"], cwd=str(ROOT_DIR))


def interactive_menu():
    """Interactive text menu for quick navigation."""
    print_banner()
    print("""
  [1] Start All Services (API + Workstation + Investigator)
  [2] Start FEAS Workstation UI (Port 8501)
  [3] Start FEAS FastAPI Backend (Port 8000)
  [4] Start Deep Learning Investigator UI (Port 8502)
  [5] Start React 3D Dashboard (Vite)
  [6] Run Comprehensive Test Suite (94+ Tests)
  [7] System & Platform Diagnostics (Doctor)
  [8] Install / Sync Dependencies for this Platform
  [9] Launch via Docker Compose
  [0] Exit
""")
    try:
        choice = input("Select an option [1-9, 0]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nExiting.")
        return

    actions = {
        "1": lambda: run_services(["all"]),
        "2": lambda: run_services(["workstation"]),
        "3": lambda: run_services(["api"]),
        "4": lambda: run_services(["investigator"]),
        "5": lambda: run_services(["frontend"]),
        "6": run_tests,
        "7": run_doctor,
        "8": run_setup,
        "9": run_docker,
        "0": lambda: sys.exit(0),
    }

    action = actions.get(choice)
    if action:
        action()
    else:
        print(f"{RED}Invalid option: {choice}{RESET}")


def main():
    parser = argparse.ArgumentParser(
        description="FEAS 2.0 Universal Cross-Platform Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=[
            "all",
            "feas",
            "api",
            "workstation",
            "ui",
            "investigator",
            "frontend",
            "test",
            "doctor",
            "setup",
            "docker",
        ],
        help="Command to run (if omitted, interactive menu is shown)",
    )

    args = parser.parse_args()

    if not args.command:
        interactive_menu()
    elif args.command == "doctor":
        run_doctor()
    elif args.command == "setup":
        run_setup()
    elif args.command == "test":
        run_tests()
    elif args.command == "docker":
        run_docker()
    elif args.command in ["workstation", "ui"]:
        run_services(["workstation"])
    else:
        run_services([args.command])


if __name__ == "__main__":
    main()
