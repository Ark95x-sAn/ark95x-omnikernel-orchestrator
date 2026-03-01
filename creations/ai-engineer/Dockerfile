FROM python:3.12-slim
WORKDIR /app
COPY app.py .
RUN pip install --no-cache-dir fastapi uvicorn
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:8501/ || exit 1
CMD ["python", "app.py"]
