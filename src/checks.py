import shutil
import subprocess
import re
import os
import sys
from dataclasses import dataclass, field

# Calculates free amount of space on the machine
total, used, free = shutil.disk_usage("/")

total, used, free = (round(x / (1024 ** 3), 2) for x in (total, used, free))

usedp = round((used / total) * 100)

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
STATUS_COLOR = {"OK": "32", "WARN": "33", "FAIL": "31"}  # green, yellow, red

# Optionally decorate text with terminal styling.
def paint(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else text

@dataclass
class CheckResult:
    name: str
    status: str                      # "OK", "WARN" or "FAIL"
    summary: str
    details: list[str] = field(default_factory=list)

def check_updates(upgrades: list) -> CheckResult:
    security = sum(upgrade.is_security for upgrade in upgrades) # Sum of security updates.
    if not upgrades:
        return CheckResult("Updates", "OK", "System is up to date")

    status = "FAIL" if security else "WARN"
    summary = f"{len(upgrades)} updates pending ({security} security)"

    width = max(len(upgrade.name) for upgrade in upgrades[:10]) # Length of the longest name in top 10 of the list. It makes the output more readable.
    details = [
        f"{upgrade.name:<{width}}  {upgrade.old_version} -> {upgrade.new_version}"
        for upgrade in upgrades[:10]
    ]
    if len(upgrades) > 10:
        details.append(f"... and {len(upgrades) - 10} more")
    return CheckResult("Updates", status, summary, details)

def print_report(results: list[CheckResult]) -> int:
    print(paint("Ubuntu Health Check", "1"))   # 1 = bold
    print("-" * 44)

    print(f"Total space: {total} GB")
    print(f"Total used: {used} GB ({usedp}% used)")
    print(f"Total free space: {free} GB")
    print("-" * 44)

    for result in results:
        label = paint(f"[ {result.status:<4} ]", STATUS_COLOR[result.status])
        print(f"{label} {result.name}: {result.summary} \n")
        for line in result.details:
            print(f"{line}")

    worst = max((result.status for result in results), # Determine the worst status among all results.
                key=["OK", "WARN", "FAIL"].index)
    print("-" * 44)
    print(f"Overall: {paint(worst, STATUS_COLOR[worst])}")
    return {"OK": 0, "WARN": 1, "FAIL": 2}[worst]

result_list = check_updates(get_pending_updates())
print_report([result_list])