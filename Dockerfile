FROM python:3.11-slim

# Install system dependencies including Git
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Download Spacy model
RUN python -m spacy download en_core_web_sm

# Copy remaining code files
COPY . .

# Expose port (default for FastAPI / HF is 8000 or 7860, we read from $PORT environment variable)
ENV PORT=8000
EXPOSE 8000

# Start app using Uvicorn
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT}"]