FROM python:3.12-slim
WORKDIR /app
COPY requirements.lock.txt ./
RUN pip install --no-cache-dir -r requirements.lock.txt
COPY pyproject.toml README.md LICENSE NOTICE MANIFEST.in ./
COPY ads_mcp ./ads_mcp
RUN pip install --no-cache-dir --no-deps . && useradd --create-home --uid 10001 ads && mkdir /data && chown ads:ads /data
USER ads
ENV GOOGLE_ADS_MCP_HOST=0.0.0.0 PORT=8080 GOOGLE_ADS_MCP_REPORT_DB=/data/reports.sqlite3 GOOGLE_ADS_MCP_STORAGE_PATH=/data/oauth
EXPOSE 8080
CMD ["ads-command-center", "serve"]
