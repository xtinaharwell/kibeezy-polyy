FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APP_HOME=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR $APP_HOME

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . .

# Create staticfiles directory
RUN mkdir -p /app/staticfiles && \
    mkdir -p /app/logs

# Collect static files (if needed in image)
# RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run gunicorn
CMD ["gunicorn", "--config", "gunicorn_config.py", "api.wsgi:application"]
