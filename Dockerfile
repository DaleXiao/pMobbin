# Dockerfile

# Lightweight Python image
FROM python:3.10-slim

# Set working dir
WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all code to working dir
COPY . .

# Declare the port
EXPOSE 8000

# Define the command to start docker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
