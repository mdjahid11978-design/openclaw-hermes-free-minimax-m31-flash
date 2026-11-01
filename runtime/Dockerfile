FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 JAHIDS_HOST=0.0.0.0 JAHIDS_PORT=8787
WORKDIR /app
COPY pyproject.toml ./
COPY jahids_runtime ./jahids_runtime
RUN pip install --no-cache-dir .
RUN useradd --create-home --uid 10001 jahids && mkdir -p /app/data && chown -R jahids:jahids /app
USER jahids
EXPOSE 8787
CMD ["jahids-runtime"]
