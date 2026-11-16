# MiTallercito – imagen Docker (alternativa a Proxmox/LXC)
FROM python:3.15-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    MT_DATA_DIR=/data MT_DOCKER=1 PORT=8080
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && useradd -r -u 10001 -d /data mitallercito \
 && mkdir -p /data && chown mitallercito /data
COPY app.py VERSION REPO ./
COPY static ./static
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 755 /entrypoint.sh

USER mitallercito
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/api/brand',timeout=4)"
ENTRYPOINT ["/entrypoint.sh"]
