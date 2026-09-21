FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOME=/home/appuser

WORKDIR /app

RUN addgroup \
        --system \
        --gid 10001 \
        appgroup \
    && adduser \
        --system \
        --uid 10001 \
        --ingroup appgroup \
        --home /home/appuser \
        appuser \
    && mkdir -p /home/appuser \
    && chown -R 10001:10001 /home/appuser

COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY --chown=10001:10001 . .

RUN chmod +x /app/docker-entrypoint.sh

USER 10001:10001

EXPOSE 5000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
