# Ubuntu Health Checker

A command-line tool written in Python that checks the health of an Ubuntu system by reporting disk usage, pending package updates, failed system services, reboot requirements, and backup age. It then displays a summary of the system's health.

## Features

- **Disk Usage:** Reports total, used, and available disk space.
- **Package Updates:** Checks for pending package updates and identifies security updates.
- **Failed Services:** Checks for failed systemd services.
- **Reboot Status:** Checks whether the system requires a reboot.
- **System Updates:** Supports upgrading installed packages through the `--update` option.

## Requirements

- Ubuntu Linux
- Python 3
- `sudo` privileges for operations that require elevated permissions

## Installation

Clone the repository and navigate to the project directory:

```bash
git clone https://github.com/n1ckOnGithub/ubuntuhealthchecker.git
cd ubuntuhealthchecker
```

## Usage

### Run a health check

```bash
python3 src/healthcheck.py
```

### Display additional details

```bash
python3 src/healthcheck.py --verbose
```

### Upgrade installed packages

```bash
python3 src/healthcheck.py --update
```

The update operation may require `sudo` authentication. Review the packages that will be upgraded before running the command.

## Example Output

The tool displays a summary of each check, followed by additional details where applicable.

```text
\ Refreshing package lists...

Ubuntu Health Check
--------------------------------------------
[ OK   ] Disk Usage: 26% used (321.04 GB free)
[ OK   ] Disk Usage: 26% used (321.04 GB free)
[ WARN ] Updates: 1 updates pending (0 security)
[ OK   ] Services: 0 services failed
[ OK   ] Reboot: No reboot required

--------------------------------------------
```

## Limitations

- The tool is designed for Ubuntu systems and relies on Linux system utilities.
- Package update results depend on the package information available on the system.
- Backup status depends on how the tool identifies the most recent backup.
- The update operation requires appropriate permissions and may fail if package management encounters errors or another process holds the package manager lock.

## Project Purpose

This project was built to develop practical Python programming and Linux system administration skills by creating a command-line tool for monitoring system health.
