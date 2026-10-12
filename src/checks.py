import shutil
import subprocess
import re
import os
import sys
from dataclasses import dataclass, field

update_results = []

@dataclass
class CheckResult:
    name: str
    status: str                      # "OK", "WARN" or "FAIL"
    summary: str
    details: list[str] = field(default_factory=list)

# Calculates free amount of space on the machine
def disk_status() -> CheckResult:
    total, used, free = shutil.disk_usage("/")
    total, used, free = (round(x / (1024 ** 3), 2) for x in (total, used, free))
    p_used = round((used / total) * 100)
    return CheckResult("Disk Usage",
                        "OK" if p_used < 80 else "WARN",
                        f"{"Total Space":<11}: {total} GB, \n{"Total Used":<11}: {used} GB, ({p_used}% used) \n{"Total Free":<11}: {free} GB,",
                        {"total": total, "used": used, "free": free, "p_used": p_used}) 

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
    status = "PEND"
    summary = f"{len(upgrades)} updates pending ({security} security)"

    width = max(len(upgrade.name) for upgrade in upgrades[:10]) # Length of the longest name in top 10 of the list. It makes the output more readable.
    details = [
        f"{upgrade.name:<{width}}: {upgrade.old_version} -> {upgrade.new_version}" for upgrade in upgrades
    ]

    return CheckResult("Updates", status, summary, details)

def summary_print(disk_result: CheckResult, update_result: CheckResult) -> None:
    disk_label = paint(f"[ {disk_result.status:<4} ]", STATUS_COLOR[disk_result.status])
    print(f"{disk_label} {disk_result.name}: {disk_result.details['p_used']}% used ({disk_result.details['free']} GB free)")

    update_label = paint(f"[ {update_result.status:<4} ]", STATUS_COLOR[update_result.status])
    print(f"{update_label} {update_result.name}: {update_result.summary}\n")


def detail_report(disk_result: CheckResult, update_result: CheckResult) -> None:
    print("Details")
    print("=" * 44)
    print()

    print(f"{disk_result.name}") # Disk usage.
    print("-" * 44)
    print(f"{disk_result.summary}\n")

    print(update_result.name) # Updates.
    print("-" * 44)
    for result in update_result.details:
            print(f"{result}")

def print_report(disk_result: CheckResult, update_result: CheckResult) -> int:
    print()
    print(paint("Ubuntu Health Check", "1"))   # 1 = bold
    print("-" * 44)

    # Summary Section
    summary_print(disk_result, update_result)

    # Details Section
    detail_report(disk_result, update_result)
    
    print("-" * 44)
    

print_report(disk_status(), check_updates(get_pending_updates()))