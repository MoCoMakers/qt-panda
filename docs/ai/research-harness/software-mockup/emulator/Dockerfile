FROM python:3.11-slim

RUN pip install --no-cache-dir numpy

WORKDIR /app
COPY stm_emulator.py /app/

EXPOSE 9000
CMD ["python", "-u", "stm_emulator.py"]
