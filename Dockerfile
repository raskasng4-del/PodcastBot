FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    fonts-noto \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i 's|<policy domain="path" rights="none" pattern="@*"/>|<policy domain="path" rights="read|write" pattern="@*"/>|' /etc/ImageMagick-6/policy.xml || true

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY abdo.png .

CMD ["python", "bot.py"]
