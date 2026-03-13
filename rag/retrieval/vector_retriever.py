from typing import Dict, Any, Optional, List, Tuple

from infra.logs.logger_config import setup_logger
from rag.vector_store.pinecone_store import PineconeStore

logger = setup_logger("rag.vector_retriever")


def _parse_query_rules(query: str) -> Optional[Dict[str, Any]]:
    """
    简单规则解析器，根据查询内容生成 metadata 过滤条件
    """
    query_lower = query.lower()

    # 简历
    resume_keywords = [
        "简历",
        "个人简",
        "应聘",
        "求职者",
        "工作经历",
        "教育背景",
        "项目经验",
        "技能",
    ]

    if any(keyword in query_lower for keyword in resume_keywords):
        logger.info("Matched resume-related keywords")
        return {"document_type": "个人简历"}

    # 制度
    policy_keywords = ["考核", "制度", "办法", "规定", "条例", "细则", "政策"]

    if any(keyword in query_lower for keyword in policy_keywords):
        logger.info("Matched policy-related keywords")
        return {"document_type": "银行管理制度"}

    # 合同
    contract_keywords = ["合同", "协议", "签约", "协定"]

    if any(keyword in query_lower for keyword in contract_keywords):
        logger.info("Matched contract-related keywords")
        return {"document_type": "合同协议"}

    # 报告
    report_keywords = ["报告", "总结", "汇报", "述职"]

    if any(keyword in query_lower for keyword in report_keywords):
        logger.info("Matched report-related keywords")
        return {"document_type": "报告总结"}

    logger.info("No matching rules, will search all documents")
    return None


def _is_pinecone_store(vector_store: Any) -> bool:
    """检查是否是 Pinecone Store"""
    try:
        return isinstance(vector_store, PineconeStore)
    except Exception:
        return False


def _retrieve_from_pinecone(
    pinecone_store: PineconeStore,
    query: str,
    k: int,
    filter_condition: Optional[Dict[str, Any]] = None,
):
    """Pinecone 检索"""
    try:
        results = pinecone_store.similarity_search(
            query=query,
            k=k,
            filter_metadata=filter_condition,
        )

        from langchain_core.documents import Document

        docs: List[Tuple[Document, float]] = []

        for vector_id, score, metadata in results:
            doc = Document(
                page_content=metadata.get("text", ""),
                metadata=metadata,
            )
            docs.append((doc, score))

        logger.info(
            f"Pinecone retrieval returned {len(docs)} documents with filter: {filter_condition}"
        )

        return docs

    except Exception as e:
        logger.error(f"Pinecone retrieval failed: {e}", exc_info=True)
        return []


def _retrieve_from_faiss(
    db: Any,
    query: str,
    k: int,
    filter_condition: Optional[Dict[str, Any]] = None,
):
    """FAISS 检索"""
    candidate_k = max(20, k * 5)

    all_docs = db.similarity_search_with_score(query, k=candidate_k)

    logger.info(f"Retrieved {len(all_docs)} candidate documents")

    sources_found = set()

    for i, (doc, score) in enumerate(all_docs[:15]):
        source = doc.metadata.get("source", "unknown")
        sources_found.add(source)

        content_preview = doc.page_content[:80].replace("\n", " ").strip()

        logger.info(f"Candidate {i+1}: score={score:.4f}, source={source}")
        logger.info(f"  Content: {content_preview}...")

    logger.info(
        f"Found documents from {len(sources_found)} different sources: {sources_found}"
    )

    if not all_docs:
        logger.warning(f"No documents found for query: {query}")
        return []

    # 排序
    all_docs.sort(key=lambda x: x[1])

    if filter_condition:
        logger.info(f"Applying filter: {filter_condition}")

        filtered_docs = [
            (doc, score)
            for doc, score in all_docs
            if all(
                doc.metadata.get(key) == value
                for key, value in filter_condition.items()
            )
        ]

        logger.info(
            f"Filtered from {len(all_docs)} to {len(filtered_docs)} documents"
        )

        return filtered_docs[:k]

    return all_docs[:k]


def retrieve_with_score(
    vector_store: Any,
    query: str,
    k: int,
    filter_metadata: Optional[Dict[str, Any]] = None,
):
    """
    检索带分数的文档（使用简单规则解析）

    :param vector_store: 向量库实例（FAISS 或 PineconeStore）
    :param query: 用户问题
    :param k: 返回数量
    :param filter_metadata: 兼容参数，目前未使用
    :return: [(Document, score), ...]
    """
    logger.debug(f"Performing search with k={k}")

    # Step 1: 规则解析
    filter_condition = _parse_query_rules(query)

    logger.info(f"Query: {query}")
    logger.info(f"Generated filter condition: {filter_condition}")

    # Step 2: 检索
    if _is_pinecone_store(vector_store):
        return _retrieve_from_pinecone(
            vector_store, query, k, filter_condition
        )
    else:
        return _retrieve_from_faiss(
            vector_store, query, k, filter_condition
        )

