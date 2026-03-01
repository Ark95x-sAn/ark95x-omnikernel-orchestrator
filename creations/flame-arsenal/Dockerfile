FROM python:3.12-slim
WORKDIR /app
COPY arsenal.py .
RUN pip install --no-cache-dir fastapi uvicorn
EXPOSE 8502
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8502/ || exit 1
CMD ["python", "arsenal.py"]
