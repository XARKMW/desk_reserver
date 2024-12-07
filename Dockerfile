FROM python:3.8-slim

# Install Chrome and Chrome WebDriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV BOOKING_USERNAME=""
ENV BOOKING_PASSWORD=""
ENV BOOKING_URL=""

# Run the bot
CMD ["python", "desk_booking_bot.py"]