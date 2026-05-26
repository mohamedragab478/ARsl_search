FROM python:3.11-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user

WORKDIR /app

COPY requirements.txt README.md ./

# install as ROOT
RUN uv pip install --system -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --index-strategy unsafe-best-match

COPY --chown=user app/ ./app/
COPY --chown=user KARSL-502_Labels.xlsx ./
COPY --chown=user sign_search.py ./

RUN wget -q --show-progress \
    "https://github.com/mohamedragab478/ARsl_search/releases/download/ARsl_search/data_gifs.zip" \
    -O /tmp/data_gifs.zip \
    && python3 -c "\
import zipfile, os; \
z = zipfile.ZipFile('/tmp/data_gifs.zip'); \
os.makedirs('/app/data_gifs', exist_ok=True); \
[z.extract(m, '/app/data_gifs') for m in z.namelist()]; \
" \
    && find /app/data_gifs -mindepth 2 -name '*.gif' -exec mv {} /app/data_gifs/ \; 2>/dev/null || true \
    && rm /tmp/data_gifs.zip \
    && chown -R user:user /app

# Switch to non-root user for security (required by Hugging Face Spaces)
USER user

ENV PATH="/home/user/.local/bin:$PATH"

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]