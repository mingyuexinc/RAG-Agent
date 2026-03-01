import logging
from typing import List, Tuple
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from infra.config.app_config import AppConfig


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

def process_text_with_splitter(text:str) -> list[str]:

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

def data_loader(file_path):
    try:
        pdf = PdfReader(file_path)
        text, page_numbers = extract_text_with_page_numbers(pdf)
        chunks = process_text_with_splitter(text)
    except Exception as e:
        logging.error(f"Error processing file: {str(e)}")
        raise e
    return chunks

# unit test
# if __name__ == "__main__":
#     loader_path = "./assets"
#     chunks_test = data_loader(loader_path)
#     print(chunks_test)