# Multi-stage Dockerfile for libvirt-mcp-server
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    libvirt-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install uv

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock* ./
COPY libvirt_mcp_server/ ./libvirt_mcp_server/
COPY README.md ./

# Install dependencies and build wheel
RUN uv venv && \
    . .venv/bin/activate && \
    uv sync --frozen && \
    uv build


# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libvirt0 \
    libvirt-clients \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r libvirt && useradd -r -g libvirt -d /app -s /bin/bash libvirt

# Set working directory
WORKDIR /app

# Copy built wheel from builder stage
COPY --from=builder /app/dist/*.whl ./

# Install the application
RUN pip install --no-cache-dir *.whl && \
    rm *.whl

# Copy configuration template
COPY config.example.yaml ./config.yaml

# Create directories for logs and configs
RUN mkdir -p /app/logs /app/configs && \
    chown -R libvirt:libvirt /app

# Switch to non-root user
USER libvirt

# Expose port for HTTP/SSE transport
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD libvirt-mcp-server --health-check || exit 1

# Default command
CMD ["libvirt-mcp-server", "--config", "/app/config.yaml"]
