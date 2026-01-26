# Barndoor Deployment Guide

## 1. Requirements
To make this site available online, you need a hosting server (VPS).
Recommended providers:
- **DigitalOcean** ($5/mo Droplet)
- **Vultr**
- **AWS Lightsail**
- **Linode**

**Specs**: Ubuntu 22.04 LTS (preferred), 1GB RAM minimum.

## 2. What I Need From You
Once you purchase a server, please provide:
- **IP Address**: (e.g., `142.93.xxx.xxx`)
- **Username**: usually `root`
- **Password**: (or instructions for SSH key if you set one up)

## 3. Deployment Steps (What I Will Do)
Once I have access, I will run the following to make the site live 24/7:

1.  **System Setup**:
    ```bash
    sudo apt update && sudo apt install -y python3-pip python3-venv nginx
    ```

2.  **Application Installation**:
    - Clone the code to `/var/www/barndoor`.
    - Install dependencies (`pip install -r requirements.txt`).

3.  **Process Management (Systemd)**:
    - Create a service so the app restarts if it crashes or the server reboots.
    - `gunicorn --workers 3 --bind unix:barndoor.sock -m 007 web_server:app`

4.  **Web Server (Nginx)**:
    - Proxy traffic from port 80 (HTTP) to the application.
    - Set up the domain name (if you have one).

5.  **Security**:
    - Enable firewall (`ufw allow 'Nginx Full'`).
    - Set up HTTPS (SSL) using Certbot if you have a domain name.

## 4. Local Testing
Your local version is now protected!
- **URL**: `http://localhost:5000`
- **Login**: `admin`
- **Password**: `password` (Change this in `web_server.py` line 18)
