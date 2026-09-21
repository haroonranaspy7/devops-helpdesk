FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/appuser

WORKDIR /app

RUN addgroup --system appgroup \
    && adduser --system --ingroup appgroup appuser \
    && mkdir -p /home/appuser \
    && chown -R appuser:appgroup /home/appuser

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY --chown=appuser:appgroup . .

RUN chmod +x /app/docker-entrypoint.sh

USER appuser

EXPOSE 5000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
