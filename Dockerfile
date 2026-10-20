FROM python:3.10-slim

# Install C dependencies for FLINT & GMP
RUN apt-get update && apt-get install -y \
    build-essential \
    libgmp-dev \
    libmpfr-dev \
    libflint-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--timeout", "120", "--workers", "1", "--bind", "0.0.0.0:5000", "app:app"]
