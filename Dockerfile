FROM python:3.9-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    imagemagick \
    fonts-hosny-amiri \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN sed -i 's/rights="none" pattern="@\*"/rights="read|write" pattern="@\*"/g' /etc/ImageMagick-6/policy.xml

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY abdo.png .

CMD ["python", "bot.py"]
