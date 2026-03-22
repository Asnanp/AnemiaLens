FROM python:3.11-slim

WORKDIR /app

# System deps for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install only Render runtime deps first.
COPY backend/requirements-render.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements-render.txt

# Copy backend source
COPY backend/ .

EXPOSE 5000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5000"]
