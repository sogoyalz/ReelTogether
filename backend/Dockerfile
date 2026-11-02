FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////data/movie_analytics.db \
    HOME=/tmp

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN groupadd --gid 10001 reel && useradd --uid 10001 --gid reel --no-create-home reel \
    && mkdir -p /data /erasure-ledger && chown reel:reel /data /erasure-ledger

USER 10001:10001

EXPOSE 8000

CMD ["sh", "entrypoint.sh"]
