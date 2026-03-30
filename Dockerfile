FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force cache bust on every deploy
ARG CACHEBUST=1
COPY . .

CMD ["python", "main.py"]
