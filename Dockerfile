FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies first, separately from the source, so this layer is cached
# as long as requirements.txt doesn't change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwright browser binaries + their OS-level dependencies (apt packages).
# Add more browsers if the suite needs them, e.g. "chromium firefox webkit".
RUN playwright install --with-deps chromium

COPY . .

ENTRYPOINT ["pytest"]
