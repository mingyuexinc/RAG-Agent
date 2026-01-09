# Enterprise-level Agent Knowledge Base Assistant
## packages:
- pypdf2
- dashscope
- langchain
- langchain-openai
- langchain-community
- faiss-cpu
- fast-api
- ragas

## instruction:
    An intelligent agent assistant that supports knowledge retrieval, summary generation,
    and flowchart generation.

## run
1. Install the required packages:
2. start the FastAPI service:
    uvicorn api_server:app --host 127.0.0.1 --port 8000 --reload
3. run main.py


# result
![flow_chart_result](./assets/api_test/flow_chart_result.png)
