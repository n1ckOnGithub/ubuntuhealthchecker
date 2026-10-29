Ubuntu Health Checker

A command-line tool written in Python that checks the health of an Ubuntu system by reporting disk usage, pending package updates, failed system services, reboot requirements, and backup age. It then displays a summary of the system's health.

Features

Disk Usage: Reports total, used, and available disk space.

Package Updates: Checks for pending updates and identifies security updates.

Failed Services: Checks for failed systemd services.

Reboot Status: Checks whether the system needs to be rebooted.`

System Updates: Supports an option to upgrade installed packages.

Requirements

Ubuntu Linux

Python 3

sudo privileges for operations that require elevated permissions

Usage

Clone the repository and navigate to the project directory:

git clone https://github.com/n1ckOnGithub/ubuntuhealthchecker.git
cd ubuntuhealthchecker

Run the health check:

python3 src/healthcheck.py

Display additional details:

python3 src/healthcheck.py --verbose

Upgrade installed packages:

python3 src/healthcheck.py --update

The update option may require your password to authenticate through sudo.

Limitations

The tool is designed for Ubuntu systems and relies on Linux system utilities.

Package update checks depend on the system's available package information.

Backup status depends on how the tool identifies the most recent backup.

The update option requires appropriate permissions and may fail if package management is unavailable or encounters errors.
