FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir --editable ".[dev]"

COPY manage.py ./
COPY docker/entrypoint.sh /usr/local/bin/ordersync-entrypoint

RUN chmod +x /usr/local/bin/ordersync-entrypoint

ENTRYPOINT ["ordersync-entrypoint"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8010"]

