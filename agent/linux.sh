ln -s $(pwd)/womagent.service /etc/systemd/system/womagent.service
systemctl enable womagent.service
systemctl start womagent.service
