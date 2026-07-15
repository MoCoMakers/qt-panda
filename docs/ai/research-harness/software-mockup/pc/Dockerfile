# Headless PC driver: needs only socat (serial<->TCP bridge) + pyserial + numpy.
# The real pc/qtpanda source is mounted at runtime (see docker-compose.yml).
FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends socat \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir numpy pyserial

WORKDIR /app
COPY mockup_driver.py entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
