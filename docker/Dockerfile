FROM python:3.10-alpine

WORKDIR /app

# Alpine 使用 apk 包管理器
RUN apk add --no-cache gcc g++ musl-dev

COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY .. .

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "api.api_server:app", "--host", "0.0.0.0", "--port", "8000"]