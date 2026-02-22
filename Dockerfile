# Use official Python image
FROM python:3.10-slim

# Copy project code
COPY . /app

# Set working directory
WORKDIR /app

# Copy and install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8000

# Run the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]