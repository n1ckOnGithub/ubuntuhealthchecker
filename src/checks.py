import shutil
import subprocess
import re
import os
from dataclasses import dataclass

# Calculates free amount of space on the machine
total, used, free = shutil.disk_usage("/")

total, used, free = (round(x / (1024 ** 3), 2) for x in (total, used, free))

usedp = round((used / total) * 100)

#print(f"Total space: {total} GB")
#print(f"Total used: {used} GB ({usedp}% used)")
#print(f"Total free space: {free} GB")

#Check for available updates via apt
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

print(get_pending_updates())