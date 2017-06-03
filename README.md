# NoiseMapper Server

## What's this?
This repository contains the server application for my master's thesis project at UiO.  
The final text can be found [here](https://github.com/papkos/noisemapper-text).  
There is also a companion Android application, available [here](https://github.com/papkos/noisemapper-app).

## What can Noisemapper Server do?
It is a Django application, that
1. Offers an API to upload measurements taken by the Android app, and
2. Serves a simple website where the uploaded data can be browsed (on a heatmap).

## How to set up?
(at least how I did it)
1. You need a VM with a fix IP and preferably a DNS entry

2. SSL is also highly recommended

3. Install the following packages:
    ```bash
    sudo apt install nginx
    sudo apt install python3 python3-dev
    sudo apt install python3-pip
    sudo pip3 install --upgrade pip
    sudo pip3 install virtualenvwrapper
    ```

4. Clone this repository to `~/deployed/noisemapper-server`

5. Create a new virtualenv
    ```bash
    mkvirtualenv noisemapper-server \
        -a ~/deployed/noisemapper-server \
        -r ~/deployed/noisemapper-server/requirements.txt
    ```

6. Create a file at `~/deployed/env/noisemapper-server.env` with the following contents
    ```bash
    GOOGLE_MAPS_API_KEY=#<Use your own!>
    
    DJANGO_SECRET=#<Generate your own!>
    DJANGO_ALLOWED_HOSTS=#<Your registered domain name, e.g. mysite.com>
    
    API_SECRET=#<Generate your own, needed by noisemapper-app too!>
    SNIPPET_STORAGE_DIR=~/snippet_storage
    # 75 MB, keep in sync with nginx
    MAX_POST_PAYLOAD=78643200
    
    # Shouldn't be true in production!!! 
    #DEBUG=true
    ```

7. Create a new systemd unit, like this:
    ```bash
    [Unit]
    Description=uWSGI instance to serve the NoiseMapper server
    
    [Service]
    Environment="VENV_PATH=/home/ubuntu/.virtualenvs/noisemapper-server"
    Environment="WORK_DIR=/home/ubuntu/deployed/noisemapper-server"
    EnvironmentFile="home/ubuntu/deployed/env/noisemapper-server.env"
    
    ExecStart=/bin/bash -c "cd ${WORK_DIR}; source ${VENV_PATH}/bin/activate; uwsgi --ini uwsgi.ini"
    
    [Install]
    WantedBy=multi-user.target
    ```
    Then make systemd pick it up by running
    ```bash
    sudo systemctl daemon-reload
    ```

8. Use the following script (save it to an executable file) to start and then later redeploy
newer versions
    ```bash
    #!/usr/bin/env bash
    
    VENV_DIR=/home/ubuntu/.virtualenvs/noisemapper-server
    read -r PROJECT_DIR < $VENV_DIR/.project
    
    source $VENV_DIR/bin/activate \
        && cd $PROJECT_DIR \
        && git pull \
        && python manage.py migrate \
        && python manage.py collectstatic --no-input \
        && sudo systemctl restart noisemapper-server.service \
        && echo "Done!"
    ```
    
9. Create an nginx config file at `/etc/nginx/sites-available/<YOUR_HOSTNAME>.conf`, with contents:
    ```
    # <YOUR_HOSTNAME>.conf
    
    # the upstream component nginx needs to connect to
    upstream django {
        # server unix:///path/to/your/mysite/mysite.sock; # for a file socket
        server 127.0.0.1:8000; # for a web port socket (we'll use this first)
    
    log_format access_log_format '{'
                                     '"status": "$status",'
    				 '"path": "$request",'
    				 '"remote": "$remote_addr",'
    				 '"bytes": "$body_bytes_sent",'
    				 '"userAgent": "$http_user_agent"'
    			      '}';
    
    # Redirect HTTP to HTTPS
    server {
        server_name    <YOUR_HOSTNAME>;
        listen         80;
        return 	   301 https://$host$request_uri;
    }
    
    
    # configuration of the server
    server {
        # the port your site will be served on
        listen      443 ssl;
        # the domain name it will serve for
        server_name <YOUR_HOSTNAME>; # substitute your machine's IP address or FQDN
        
        ssl_certificate	ssl/ca-bundle.crt;
        ssl_certificate_key ssl/<YOUR_HOSTNAME>.key;
        ssl_protocols       TLSv1 TLSv1.1 TLSv1.2;
        ssl_ciphers         HIGH:!aNULL:!MD5;
    
        charset     utf-8;
    
        # Logging
        access_log syslog:server=unix:/dev/log,tag=nginx,severity=info access_log_format;
    
        # max upload size, Keep in sync with django!
        client_max_body_size 75M;   # adjust to taste
    
        # Django media
        location /media  {
            alias /home/ubuntu/deployed/noisemapper-server/media;  # your Django project's media files - amend as required
        }
    
        location /static {
            alias /home/ubuntu/deployed/noisemapper-server/static; # your Django project's static files - amend as required
        }
    
        # Finally, send all non-media requests to the Django server.
        location / {
            uwsgi_pass  django;
            include     uwsgi_params; # the uwsgi_params file you installed
        }
    }

    ```
    Then reload nginx:
    ```bash
    sudo nginx -t && sudo nginx -s reload
    ```
