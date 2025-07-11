#!/bin/bash

# Synchronization with peer filesystem 
MASTER_DIR="/var/dir/"
SLAVE_DIR="/var/dir/"
LOG_FILE="/var/log/rsync.log"
IDENTITY_FILE="/home/syncuser/.ssh/id_ed25519"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
}

# Function to perform sync
sync_directories() {
    log_message "Starting sync from master to slave"
    rsync -avzur -e "ssh -i $IDENTITY_FILE -p <port>" --delete $MASTER_DIR syncuser@<hostname>:$SLAVE_DIR
    if [ $? -eq 0 ]; then
        log_message "Sync from master to slave completed successfully"
    else
        log_message "Error during sync from master to slave: $?"
    fi

    log_message "Starting sync from slave to master"
    rsync -avzur -e "ssh -i $IDENTITY_FILE -p <port>" syncuser@<hostname>:$SLAVE_DIR $MASTER_DIR
    if [ $? -eq 0 ]; then
        log_message "Sync from slave to master completed successfully"
    else
        log_message "Error during sync from slave to master: $?"
    fi
}

# Function to check if master is online
is_master_online() {
    ping -c 1 -W 1 $(hostname) &> /dev/null
    return $?
}

# Function to get the latest file timestamp in a directory
get_latest_timestamp() {
    log_message "Retrieving timestamp from slave directory"
    local timestamp=$(ssh -t -i $IDENTITY_FILE -p <port> syncuser@<hostname> "find $SLAVE_DIR -type f -printf '%T@\n' | sort -n | tail -1")
    if [ -z "$timestamp" ]; then
        log_message "Error retrieving timestamp from slave directory"
        ssh -t -i $IDENTITY_FILE -p <port> syncuser@<hostname> "find $SLAVE_DIR -type f -printf '%T@\n' | sort -n | tail -1" &>> $LOG_FILE
    else
        log_message "Retrieved slave timestamp: $timestamp"
    fi
    echo $timestamp
}

# Function to decide sync direction based on latest file timestamps
decide_sync_direction() {
    local master_latest=$(find $MASTER_DIR -type f -printf '%T@\n' | sort -n | tail -1)
    local slave_latest=$(get_latest_timestamp)

    log_message "Master latest timestamp: $master_latest"
    log_message "Slave latest timestamp: $slave_latest"

    if [ -z "$slave_latest" ]; then
        log_message "Slave timestamp is empty, defaulting to master to slave sync"
        rsync -avzur -e "ssh -i $IDENTITY_FILE -p <port>" --delete $MASTER_DIR syncuser@<hostname>:$SLAVE_DIR
        if [ $? -eq 0 ]; then
            log_message "Sync from master to slave completed successfully"
        else
            log_message "Error during sync from master to slave: $?"
        fi
    elif (( $(echo "$slave_latest > $master_latest" | bc -l) )); then
        log_message "Slave has the latest files, syncing slave to master"
        rsync -avzur -e "ssh -i $IDENTITY_FILE -p <port>" --delete syncuser@<hostname>:$SLAVE_DIR $MASTER_DIR
        if [ $? -eq 0 ]; then
            log_message "Sync from slave to master completed successfully"
        else
            log_message "Error during sync from slave to master: $?"
        fi
    else
        log_message "Master has the latest files, syncing master to slave"
        rsync -avzur -e "ssh -i $IDENTITY_FILE -p <port>" --delete $MASTER_DIR syncuser@<hostname>:$SLAVE_DIR
        if [ $? -eq 0 ]; then
            log_message "Sync from master to slave completed successfully"
        else
            log_message "Error during sync from master to slave: $?"
        fi
    fi
}

# Monitor directory for changes
log_message "Starting directory monitoring"
while true; do
    if is_master_online; then
        log_message "Master is online, deciding sync direction"
        decide_sync_direction
        inotifywait -m -r -e modify,create,attrib,delete $MASTER_DIR | while read path action file; do
            log_message "Detected $action on $file in $path"
            sync_directories
        done
    else
        log_message "Master is offline, waiting to retry"
        sleep 60
    fi
done
