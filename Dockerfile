FROM python:3.13-slim
WORKDIR /app
COPY requirements-production.txt /app/requirements-production.txt
RUN pip install --no-cache-dir -r /app/requirements-production.txt
COPY . /app
ENV HOST=0.0.0.0 \
    PORT=8080 \
    EINVITE_DATA_DIR=/data
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=3)" || exit 1
CMD ["python", "server.py", "--host", "0.0.0.0"]
