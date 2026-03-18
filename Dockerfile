FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python deps first (layer cache)
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY backend/ .

# Lock PyTorch to single thread for memory-constrained deployments
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# Production: uvicorn with FastAPI (single worker — memory constrained)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "5000", \
     "--workers", "1", \
     "--timeout-keep-alive", "30", \
     "--limit-concurrency", "4"]
