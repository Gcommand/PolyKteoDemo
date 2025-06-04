﻿FROM python:3.11-slim

# Attempt to update C++ runtime - CAUTION!
RUN apt-get update && apt-get install -y --only-upgrade libstdc++6 gcc g++ # May need specific versions or sources

WORKDIR /app
COPY . /app

RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (though this is just documentation)
EXPOSE 8000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-8000} app:app"]