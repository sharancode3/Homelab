FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLATFORM_ENVIRONMENT="production"

# Create app directory and non-root user
WORKDIR /app
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --gid 1001 appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY ./app /app/app

# Set ownership for app and storage directories
RUN chown -R appuser:appgroup /app && \
    mkdir -p /var/lib/auth-service/data && \
    chown -R appuser:appgroup /var/lib/auth-service

# Switch to non-root user
USER appuser

EXPOSE 8000

# Start application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]