# RF983 MOTION 0.9.0 — single-service public deployment image
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends nginx gettext-base ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/rf983
COPY backend/requirements.txt /opt/rf983/backend/requirements.txt
RUN pip install -r /opt/rf983/backend/requirements.txt
COPY backend/app /opt/rf983/backend/app
COPY frontend /usr/share/nginx/html
COPY deploy/nginx.conf.template /etc/nginx/templates/default.conf.template
COPY deploy/start.sh /usr/local/bin/rf983-start
RUN chmod +x /usr/local/bin/rf983-start
ENV PORT=10000 RF983_STATE_DB=/tmp/rf983-motion.sqlite3 RF983_ARTIFACT_DIR=/tmp/rf983-artifacts
EXPOSE 10000
CMD ["/usr/local/bin/rf983-start"]
