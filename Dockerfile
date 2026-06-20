FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# SQLite history lives here — mount a volume at /app/data to persist it
EXPOSE 8000

CMD ["uvicorn", "youtube_summarizer.main:app", "--host", "0.0.0.0", "--port", "8000"]
