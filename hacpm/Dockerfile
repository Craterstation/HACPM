ARG BUILD_FROM
FROM ${BUILD_FROM}

# Install build dependencies (needed for compiling Python packages like regex/dateparser)
RUN apk add --no-cache \
    python3 \
    py3-pip \
    python3-dev \
    gcc \
    musl-dev \
    jpeg-dev \
    zlib-dev \
    sqlite \
    jq \
    curl

# Install Python dependencies system-wide
COPY requirements.txt /tmp/
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt

# Remove build-only dependencies to reduce image size
RUN apk del --no-cache python3-dev gcc musl-dev

# Copy application
COPY backend/ /app/backend/
COPY frontend/ /app/frontend/
COPY run.sh /

# Make run script executable
RUN chmod a+x /run.sh

WORKDIR /app

CMD ["/run.sh"]
