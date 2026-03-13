import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from infra.config.app_config import AppConfig

def fixed_size_splitter(text:str) -> list[str]:

    # create text splitter
    text_spliter = RecursiveCharacterTextSplitter(
        separators = ["\n\n", "\n", " ",".",""],
        chunk_size = AppConfig.vector.CHUNK_SIZE,
        chunk_overlap = AppConfig.vector.CHUNK_OVERLAP,
        length_function = len,
    )

    chunks = text_spliter.split_text(text)
    logging.debug(f"Text split into {len(chunks)} chunks")
    return chunks