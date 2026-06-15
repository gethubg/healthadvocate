FROM python:3.12-slim

WORKDIR /app

# Install deps first for better layer caching.
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -e .

EXPOSE 8000

# Storage dirs are created at startup via Settings.ensure_dirs().
CMD ["uvicorn", "healthadvocate.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
