import logging
from typing import Tuple, List
from PyPDF2 import PdfReader

from infra.logs.logger_config import get_logger
from rag.ingestion.loaders.base_loader import BaseLoader
from rag.ingestion.splitters.fixed_size_splitter import fixed_size_splitter


logger = get_logger("rag.ingestion.loaders")

class PDFLoader(BaseLoader):
    """PDF文档加载器"""

    def load(self, file_path: str) -> str:
        """加载PDF文档"""
        try:
            pdf = PdfReader(file_path)
            text = ""
            for page_number, page in enumerate(pdf.pages, start=1):
                extracted_text = page.extract_text()
                if extracted_text:
                    text += extracted_text
                else:
                    logger.warning(f"No text found on page {page_number}")
            return text
        except Exception as e:
            logger.error(f"Error loading PDF file {file_path}: {e}")
            raise

def data_loader_core(file_path):
    """核心文档加载函数，不包含元数据管理"""
    try:
        pdf = PdfReader(file_path)
        text, page_numbers = extract_text_with_page_numbers(pdf)
        chunks = fixed_size_splitter(text)
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        raise e
    return chunks


def extract_text_with_page_numbers(pdf) -> Tuple[str, List[int]]:

    text = ""
    page_numbers = []

    for page_number,page in enumerate(pdf.pages, start=1):
        extracted_text = page.extract_text()
        if extracted_text:
            text += extracted_text
            page_numbers.extend([page_number] * len(extracted_text.split('\n')))
        else:
            logging.warning(f"No text found on page {page_number}")
    return text, page_numbers