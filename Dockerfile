FROM certbot/certbot

COPY . src/certbot-dns-gratisdns

RUN pip install --no-cache-dir --editable src/certbot-dns-gratisdns
