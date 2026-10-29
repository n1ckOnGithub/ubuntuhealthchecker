import argparse
import shutil
import subprocess
import re
import os
import sys
from dataclasses import dataclass, field
import threading
import time

def main():
    parser, args = parse_args()

    if args.help:
        parser.print_help()
        return

    disk_result = disk_status()
    refresh_result = refresh_package_lists()
    reboot_result = reboot_required()
    service_result = check_services()

    if refresh_result.status == "OK":
        updates = get_pending_updates()
        check_update = check_updates(updates)

        if args.update: 
            update_result = update_system() # update the packages.
            print(update_result.summary) 
        else:
            print_report(disk_result, check_update, service_result, reboot_result, args.verbose)
    
    else:
        print("Could not verify pending updates")

    

@dataclass
class CheckResult:
    name: str
    status: str                      # "OK", "WARN" or "FAIL"
    summary: str
    details: list[str] = field(default_factory=list)

# Calculates free amount of space on the machine
def disk_status() -> CheckResult:
    total, used, free = shutil.disk_usage("/")
    p_used = round((used / total) * 100)

    total_gb, used_gb, free_gb = (
        round(x / (1024 ** 3), 2)
        for x in (total, used, free)
    )

    if p_used < 80:
        status = "OK"
    elif p_used < 90:
        status = "WARN"
    else:
        status = "FAIL"

    summary = f"{p_used}% used ({free_gb} GB free)"

    details = [
        f'{"Total Space":<11}: {total_gb} GB',
        f'{"Total Used":<11}: {used_gb} GB',
        f'{"Total Free":<11}: {free_gb} GB',
    ]

    return CheckResult("Disk Usage", status, summary, details)

# Regex expression to extract relevant info from output.
LINE = re.compile(
    r"^(?P<name>[^/\s]+)/(?P<suites>\S+)\s+"
    r"(?P<new>\S+)\s+(?P<arch>\S+)\s+"
    r"\[upgradable from: (?P<old>[^\]]+)\]"
)

@dataclass
class Upgrade:
    name: str
    suites: list[str]
    new_version: str
    arch: str
    old_version: str

    @property
    def is_security(self) -> bool:
        return any("security" in s for s in self.suites)

def parse_upgradable(text: str) -> list[Upgrade]:
    upgrades = []
    for line in text.splitlines():
        match = LINE.match(line.strip())
        if not match:          # Skip unexpected stuff.
            continue
        upgrades.append(Upgrade(
            name=match["name"],
            suites=match["suites"].split(","),
            new_version=match["new"],
            arch=match["arch"],
            old_version=match["old"],
        ))
    return upgrades

def refresh_package_lists() -> CheckResult:
    auth = subprocess.run(
        ["sudo", "-v"],
        timeout=120,
    )

    if auth.returncode != 0:
        return CheckResult(
            "Repository Refresh",
            "WARN",
            "Sudo authentication failed",
        )

    stop_event = threading.Event()

    spinner_thread = threading.Thread(target=spinner, args=(stop_event,))

    try:
        spinner_thread.start()

        result = subprocess.run(
            ["sudo", "apt-get", "update", "-q"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            error = result.stderr.strip().splitlines()
            message = error[-1] if error else "Unknown APT error"

            return CheckResult(
                "Repository Refresh",
                "WARN",
                f"Could not refresh package lists: {message}",
            )

        return CheckResult(
            "Repository Refresh",
            "OK",
            "Package lists refreshed successfully",
        )

    except subprocess.TimeoutExpired:
        return CheckResult(
            "Repository Refresh",
            "WARN",
            "Repository refresh timed out",
        )

    except OSError as exc:
        return CheckResult(
            "Repository Refresh",
            "WARN",
            f"Could not run apt-get: {exc}",
        )
    
    finally:
        stop_event.set()
        spinner_thread.join()

def spinner(stop_event: threading.Event) -> None:
    symbols = ["|", "/", "-", "\\"]

    print()

    i = 0
    while not stop_event.is_set():
        print(f"\r{symbols[i % len(symbols)]} Updating package repositories...", end="", flush=True)
        i += 1
        time.sleep(0.1)

    print()

def get_pending_updates() -> list[Upgrade]:    
    result = subprocess.run(
        ["apt", "list", "--upgradable"],
        capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C"},  # keep output in English
    )
    return parse_upgradable(result.stdout)

USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ
STATUS_COLOR = {"OK": "32", "WARN": "33", "FAIL": "31", "PEND": "34"}  # green, yellow, red, blue

# Optionally decorate text with terminal styling.
def paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

def check_updates(upgrades: list[Upgrade]) -> CheckResult:  
    if not upgrades:
        return CheckResult("Updates", "OK", "System is up to date")

    security = sum(upgrade.is_security for upgrade in upgrades) # Sum of security updates.
    status = "WARN"
    summary = f"{len(upgrades)} updates pending ({security} security)"

    width = max(len(upgrade.name) for upgrade in upgrades[:10]) # Length of the longest name in top 10 of the list. It makes the output more readable.
    details = [
        f"{upgrade.name:<{width}}: {upgrade.old_version} -> {upgrade.new_version}" for upgrade in upgrades
    ]

    return CheckResult("Updates", status, summary, details)

def update_system() -> CheckResult:  
    auth = subprocess.run(
        ["sudo", "-v"]
    )

    if auth.returncode != 0:
        return CheckResult(
                "Repository Refresh",
                "WARN",
                "Sudo authentication failed",
                )

    try:
        result = subprocess.run(
            ["sudo", "apt-get", "upgrade", "-y"],
            capture_output=True,
            text=True,
            timeout= 120
        )

        if result.returncode !=0:
            error = result.stderr.strip().splitlines()
            message = error[-1] if error else "Unknown APT error"

            return CheckResult(
                "System Update",
                "WARN",
                f"System update failed: {message}",
            )

        return CheckResult(
            "System Update",
            "OK",
            "System packages updated successfully",
        )

    except subprocess.TimeoutExpired:
        return CheckResult(
            "Repository Refresh",
            "WARN",
            "Repository refresh timed out",
        )
    
    except OSError as exc:
        return CheckResult(
            "Repository Refresh",
            "WARN",
            f"Could not run apt-get: {exc}",
        )

def check_services() -> CheckResult:
    SERVICE_LINE = re.compile(r"^(\S+)\s+loaded\s+failed\s+failed\b")

    res = subprocess.run(
        ["systemctl", "list-units", "--failed", "--type=service"],
        capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C"},  # keep output in English
    )

    result = res.stdout.splitlines()

    failed_services = []

    for line in result:
        match = SERVICE_LINE.match(line.strip())

        if match:
            failed_services.append(match.group(1))

    status = "OK" if len(failed_services) == 0 else "FAIL"

    summary = f"{len(failed_services)} services failed"

    return CheckResult("Services", status, summary, failed_services)

def reboot_required() -> CheckResult:  
    return CheckResult("Reboot", "PEND", "System requires a reboot") if os.path.exists("/var/run/reboot-required") else CheckResult("Reboot", "OK", "No reboot required")

# Read tags
def parse_args():
    parser = argparse.ArgumentParser(
        description = "Check the health of an Ubuntu system.",
        add_help = False,
    )

    parser.add_argument(
        "-h", "--help",
        action = "store_true",
        help = "Show this help message and exit."
    )

    parser.add_argument(
        "-v", "--verbose",
        action = "store_true",
        help = "Show detailed information during checks."
    )

    parser.add_argument(
        "--update",
        action = "store_true",
        help = "Refresh repositories and upgrade installed packages."
    )

    args = parser.parse_args()
    return parser, args

def summary_print(disk_result: CheckResult, update_result: CheckResult, service_result: CheckResult, reboot_result: CheckResult) -> None:
    # Disk
    disk_label = paint(f"[ {disk_result.status:<4} ]", STATUS_COLOR[disk_result.status],)
    print(f"{disk_label} {disk_result.name}: {disk_result.summary}")

    # Updates
    update_label = paint(f"[ {update_result.status:<4} ]", STATUS_COLOR[update_result.status])
    print(f"{update_label} {update_result.name}: {update_result.summary}")

    # Services
    service_label = paint(f"[ {service_result.status:<4} ]", STATUS_COLOR[service_result.status])
    print(f"{service_label} {service_result.name}: {service_result.summary}")

    # Reboot
    reboot_label = paint(f"[ {reboot_result.status:<4} ]", STATUS_COLOR[reboot_result.status])
    print(f"{reboot_label} {reboot_result.name}: {reboot_result.summary}\n")

def detail_report(disk_result: CheckResult, update_result: CheckResult, service_result: CheckResult, verbose: bool) -> None:
    if verbose:
        print("Details")
        print("=" * 44)
        print()

        print(f"{disk_result.name}") # Disk usage.
        print("-" * 44)
        print(f"{disk_result.summary}\n")

        if len(update_result.details) > 0: # Updates.
            print("Pending Updates")
            print("-" * 44)
            for detail in update_result.details:
                print(detail)
            print()

        if len(service_result.details) > 0: # Services.
            print("Failed Services")
            print("-" * 44)
            for detail in service_result.details:
                print(detail)
            print()

def print_report(disk_result: CheckResult, update_result: CheckResult, service_result: CheckResult, reboot_result: CheckResult, verbose: bool) -> int:
    print()
    print(paint("Ubuntu Health Check", "1"))   # 1 = bold
    print("-" * 44)

    # Summary Section
    summary_print(disk_result, update_result, service_result, reboot_result)

    # Details Section
    detail_report(disk_result, update_result, service_result, verbose)
    
    print("-" * 44)

if __name__ == "__main__":
    main()