
# Use the official Playwright Python image which includes browsers
# This saves us from installing chrome/dependencies manually
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Set working directory
WORKDIR /app

# Install system dependencies if any additional are needed
RUN apt-get update && apt-get install -y \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to cache pip install
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Browsers are already in the base image (because we pin version in requirements.txt)
# No need to run playwright install

# Copy the rest of the application
COPY . .

# Expose the port Flask runs on
EXPOSE 5050

# Unbuffered output (crucial for logging)
ENV PYTHONUNBUFFERED=1

# Run the web server
CMD ["python3", "web_server.py"]
