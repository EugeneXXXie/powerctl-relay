FROM python:3.12-alpine
WORKDIR /app
COPY relay.py .
EXPOSE 8787
CMD ["python", "relay.py", "--config", "/data/config.json"]
