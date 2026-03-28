ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install system dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-pillow \
    nodejs \
    npm \
    sqlite

# Set up Python virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy application
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY run.sh /app/

# Create data directories
RUN mkdir -p /data/db /data/photos

WORKDIR /app
RUN chmod a+x run.sh

CMD ["/app/run.sh"]
