Script to add as a damon service

[Unit]
Description=Directory Synchronization Service
After=network.target

[Service]
Type=simple
ExecStart=/home/syncuser/synchro-with-echo.sh
Restart=always

[Install]
WantedBy=multi-user.target


Apply the new service 

 sudo systemctl daemon-reload
 
 sudo systemctl enable nsync.service
 sudo systemctl start nsync.service# Sync
Synchronization scripts to sync specific filesystems  between two Linux hosts
