FROM python:3.13-slim
WORKDIR /app
COPY requirements-production.txt /app/requirements-production.txt
RUN pip install --no-cache-dir -r /app/requirements-production.txt
RUN groupadd --gid 10001 einvite && useradd --uid 10001 --gid 10001 --no-create-home --shell /usr/sbin/nologin einvite
COPY --chown=einvite:einvite . /app
RUN mkdir -p /data && chown -R einvite:einvite /data
ENV HOST=0.0.0.0 \
    PORT=8080 \
    EINVITE_DATA_DIR=/data \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
VOLUME ["/data"]
EXPOSE 8080
USER 10001:10001
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=8s --start-period=20s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health/ready', timeout=5)" || exit 1
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "8080"]
