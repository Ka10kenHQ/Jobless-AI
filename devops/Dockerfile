# ============================================================================
# Stage 1: Base image with CUDA support
# ============================================================================
FROM nvidia/cuda:12.9.1-devel-ubuntu22.04 as base

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV CUDA_VISIBLE_DEVICES=0
ENV CUDA_HOME=/usr/local/cuda
ENV PATH=${CUDA_HOME}/bin:${PATH}
ENV LD_LIBRARY_PATH=${CUDA_HOME}/lib64:${LD_LIBRARY_PATH}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    unzip \
    wget \
    curl \
    git \
    build-essential \
    software-properties-common \
    gnupg \
    ca-certificates \
    lsb-release \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# CUDA libraries are already included in the nvidia/cuda base image

RUN ln -sf /usr/bin/python3.10 /usr/bin/python3 && \
    ln -sf /usr/bin/python3.10 /usr/bin/python

RUN wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | apt-key add - && \
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-7.0.list && \
    apt-get update && apt-get install -y mongodb-mongosh mongodb-database-tools && \
    rm -rf /var/lib/apt/lists/*

# ============================================================================
# Stage 2: Development environment
# ============================================================================
FROM base as development

WORKDIR /app

RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && apt-get install -y google-chrome-stable && \
    rm -rf /var/lib/apt/lists/*

RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` && \
    wget -N http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    rm chromedriver_linux64.zip && \
    mv chromedriver /usr/local/bin/ && \
    chmod +x /usr/local/bin/chromedriver

COPY requirements.txt .

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/logs /app/models /app/data /app/static /app/cache

# Set permissions
RUN chmod +x scripts/*.py

EXPOSE 8000

# Default command for development
CMD ["python", "scripts/serve.py", "--host", "0.0.0.0", "--port", "8000"]

# ============================================================================
# Stage 3: Production environment
# ============================================================================
FROM base as production

WORKDIR /app

COPY requirements.txt .

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install gunicorn

COPY config/ ./config/
COPY database/ ./database/
COPY inference/ ./inference/
COPY model_manager/ ./model_manager/
COPY preprocessing/ ./preprocessing/
COPY scripts/ ./scripts/
COPY static/ ./static/
COPY templates/ ./templates/
COPY training/ ./training/
COPY utils/ ./utils/
COPY data_collection/ ./data_collection/

RUN mkdir -p /app/logs /app/models /app/data /app/cache

RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "inference.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--worker-class", "uvicorn.workers.UvicornWorker"]

# ============================================================================
# Stage 4: Training environment (for model training)
# ============================================================================
FROM development as training

RUN pip install --no-cache-dir jupyter tensorboard wandb

EXPOSE 8888 6006

RUN mkdir -p /app/experiments /app/checkpoints /app/tensorboard_logs

CMD ["python", "scripts/train.py", "--languages", "english", "georgian"]
