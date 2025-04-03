import os
import subprocess
import time
from datetime import datetime

MASTER_DIR = "/var/dir/"
SLAVE_DIR = "/var/dir/"
LOG_FILE = "/var/log/rsync.log"
IDENTITY_FILE = "/home/syncuser/.ssh/id_ed25519"
SSH_PORT = "<port>"
HOSTNAME = "<hostname>"
SYNCUSER = "syncuser"

def log_message(message):
    with open(LOG_FILE, 'a') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

def sync_directories():
    log_message("Starting sync from master to slave")
    result = subprocess.run(["rsync", "-avzur", "-e", f"ssh -i {IDENTITY_FILE} -p {SSH_PORT}", "--delete", MASTER_DIR, f"{SYNCUSER}@{HOSTNAME}:{SLAVE_DIR}"], capture_output=True)
    if result.returncode == 0:
        log_message("Sync from master to slave completed successfully")
    else:
        log_message(f"Error during sync from master to slave: {result.returncode}")

    log_message("Starting sync from slave to master")
    result = subprocess.run(["rsync", "-avzur", "-e", f"ssh -i {IDENTITY_FILE} -p {SSH_PORT}", f"{SYNCUSER}@{HOSTNAME}:{SLAVE_DIR}", MASTER_DIR], capture_output=True)
    if result.returncode == 0:
        log_message("Sync from slave to master completed successfully")
    else:
        log_message(f"Error during sync from slave to master: {result.returncode}")

def is_master_online():
    result = subprocess.run(["ping", "-c", "1", "-W", "1", os.uname()[1]], capture_output=True)
    return result.returncode == 0

def get_latest_timestamp():
    log_message("Retrieving timestamp from slave directory")
    result = subprocess.run(["ssh", "-t", "-i", IDENTITY_FILE, "-p", SSH_PORT, f"{SYNCUSER}@{HOSTNAME}", f"find {SLAVE_DIR} -type f -printf '%T@\\n' | sort -n | tail -1"], capture_output=True, text=True)
    timestamp = result.stdout.strip()
    if not timestamp:
        log_message("Error retrieving timestamp from slave directory")
        subprocess.run(["ssh", "-t", "-i", IDENTITY_FILE, "-p", SSH_PORT, f"{SYNCUSER}@{HOSTNAME}", f"find {SLAVE_DIR} -type f -printf '%T@\\n' | sort -n | tail -1"], capture_output=True, text=True)
    else:
        log_message(f"Retrieved slave timestamp: {timestamp}")
    return timestamp

def decide_sync_direction():
    master_latest = subprocess.run(["find", MASTER_DIR, "-type", "f", "-printf", "%T@\\n", "|", "sort", "-n", "|", "tail", "-1"], capture_output=True, text=True).stdout.strip()
    slave_latest = get_latest_timestamp()

    log_message(f"Master latest timestamp: {master_latest}")
    log_message(f"Slave latest timestamp: {slave_latest}")

    if not slave_latest:
        log_message("Slave timestamp is empty, defaulting to master to slave sync")
        result = subprocess.run(["rsync", "-avzur", "-e", f"ssh -i {IDENTITY_FILE} -p {SSH_PORT}", "--delete", MASTER_DIR, f"{SYNCUSER}@{HOSTNAME}:{SLAVE_DIR}"], capture_output=True)
        if result.returncode == 0:
            log_message("Sync from master to slave completed successfully")
        else:
            log_message(f"Error during sync from master to slave: {result.returncode}")
    elif float(slave_latest) > float(master_latest):
        log_message("Slave has the latest files, syncing slave to master")
        result = subprocess.run(["rsync", "-avzur", "-e", f"ssh -i {IDENTITY_FILE} -p {SSH_PORT}", "--delete", f"{SYNCUSER}@{HOSTNAME}:{SLAVE_DIR}", MASTER_DIR], capture_output=True)
        if result.returncode == 0:
            log_message("Sync from slave to master completed successfully")
        else:
            log_message(f"Error during sync from slave to master: {result.returncode}")
    else:
        log_message("Master has the latest files, syncing master to slave")
        result = subprocess.run(["rsync", "-avzur", "-e", f"ssh -i {IDENTITY_FILE} -p {SSH_PORT}", "--delete", MASTER_DIR, f"{SYNCUSER}@{HOSTNAME}:{SLAVE_DIR}"], capture_output=True)
        if result.returncode == 0:
            log_message("Sync from master to slave completed successfully")
        else:
            log_message(f"Error during sync from master to slave: {result.returncode}")

def monitor_directory():
    log_message("Starting directory monitoring")
    while True:
        if is_master_online():
            log_message("Master is online, deciding sync direction")
            decide_sync_direction()
            result = subprocess.run(["inotifywait", "-m", "-r", "-e", "modify,create,attrib,delete", MASTER_DIR], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                path, action, file = line.split()
                log_message(f"Detected {action} on {file} in {path}")
                sync_directories()
        else:
            log_message("Master is offline, waiting to retry")
            time.sleep(60)

if __name__ == "__main__":
    monitor_directory()
