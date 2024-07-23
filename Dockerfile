# Use the official Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install Flask and dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port the application runs on
EXPOSE 5006

# Command to run the application
CMD ["python", "app.py"]
