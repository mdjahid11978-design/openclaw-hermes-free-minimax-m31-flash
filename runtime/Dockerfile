FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 JAHIDS_HOST=0.0.0.0 JAHIDS_PORT=8787 JAHIDS_WEB_DIR=/app/web
WORKDIR /app
COPY runtime/pyproject.toml ./runtime/pyproject.toml
COPY runtime/jahids_runtime ./runtime/jahids_runtime
COPY web ./web
WORKDIR /app/runtime
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 jahids && mkdir -p /app/data && chown -R jahids:jahids /app
USER jahids
EXPOSE 8787
CMD ["jahids-runtime"]
