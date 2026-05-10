# Python runtime (Chainlit + commercial backend)
# The React frontend is pre-built locally (npm run build) and committed as
# commercial-frontend/dist — no Node stage needed.
FROM neupaksregistry01.azurecr.io/python:3.11.9

WORKDIR /project

COPY . /project

RUN python -m pip install -r /project/requirements.txt

ENV PYTHONPATH=/project

# ── Azure AI Foundry ──
ENV FOUNDRY_PROJECT_ENDPOINT="https://openaieus2genai001.services.ai.azure.com/api/projects/openaieus2genai001-project"
ENV FOUNDRY_QUERY_ENGINE_AGENT_ID="RX-QueryEngine"
ENV FOUNDRY_ANALYST_AGENT_ID="RX-Analyst"

# ── Power BI ──
ENV PBI_WORKSPACE_ID="4435d932-4c62-46fd-ba3f-dd41a0d6d2f4"
ENV PBI_DATASET_ID="192c798b-0a94-4791-8520-0922452167aa"

# ── PBI auth: user-mode (delegated, MSAL cache) ──
# Set PBI_AUTH_MODE=mi to fall back to managed identity (legacy path).
ENV PBI_AUTH_MODE="user"
ENV PBI_USER_CLIENT_ID="e4c08c4a-a398-4955-af2f-0f63f892d049"
ENV PBI_USER_TENANT_ID="a85be8e2-4f70-43ec-a1fe-17302d408155"
ENV PBI_USER_UPN="nalbidewe@vendor.riyadhair.com"
ENV PBI_CACHE_PATH="/project/.pbi_cache.json"

# ── App ──
ENV LOG_LEVEL="INFO"

RUN chmod -R 0744 /project

CMD ["uvicorn", "app_routed:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000
