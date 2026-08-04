FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
COPY agentic ./agentic
COPY alembic ./alembic
COPY alembic.ini ./
COPY scripts ./scripts
COPY tests ./tests

# Installs both the app and its dev tools: the Test and Security Review
# agents genuinely invoke pytest/ruff/mypy as part of the governed workflow
# at runtime, not just at CI time - see agentic/agents/test_agent.py and
# agentic/agents/security_review_agent.py.
RUN pip install --no-cache-dir -e ".[dev]"

RUN mkdir -p /data
ENV DATABASE_URL=sqlite:////data/app.db

EXPOSE 8000

COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
