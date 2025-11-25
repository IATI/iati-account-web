#! /bin/bash

if [ ! -f "local-private-key.pem" ]; then
    openssl req -x509 -newkey rsa:4096 -keyout local-private-key.pem -out local-certificate.pem -sha256 -days 365 -nodes -subj "/C=GB/O=Open Data Services Co-operative Ltd./CN=api.eu.asgardeo.io"
fi

python manage.py runserver_plus 127.0.0.1:8443 --cert-file local-certificate.pem --key-file local-private-key.pem 
