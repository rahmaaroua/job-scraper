FROM selenium/standalone-chrome:120.0

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt /app/

# Switch to root to install packages
USER root

# Install Python, pip, and build dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    pkg-config \
    git \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install dependencies AS ROOT
RUN python3 -m pip install --upgrade pip setuptools wheel
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . /app

# Fix ownership of the app directory
RUN chown -R seluser:seluser /app

# Switch to seluser for running the application
USER seluser

# Expose Prometheus metrics port
EXPOSE 8000

# Start the scraper
CMD ["python3", "main.py"]