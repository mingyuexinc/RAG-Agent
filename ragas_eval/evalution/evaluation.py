from ragas.llms import llm_factory
from ragas.metrics.collections import(
    Faithfulness,
    AnswerRelevancy,
    ContextRecall,
    ContextPrecision
)
from ragas import Dataset, evaluate
from pathlib import Path
from embedding import build_embedding
from datasets import Dataset as HFDataset

from ragas_eval.rag_scripts.rag_pipeline import chat_with_query

ROOT_DIR = Path(__file__).resolve().parents[1]


def load_dataset():
    dataset = Dataset.load(
        name="eval_data",
        backend="local/csv",
        root_dir=str(ROOT_DIR)
    )
    return dataset

def generate_rag_response(dataset:Dataset):

    records = []

    ragas_llm = llm_factory(
        model="gpt-4o-mini"
    )

    for sample in dataset:
        question = sample["query"]
        ground_truth = sample["ground_truth"]

        rag_response = chat_with_query(question)
        answer = rag_response["answer"]
        contexts = [ref["content"] for ref in rag_response["references"]]

        records.append({
            "user_input":question,
            "response":answer,
            "retrieved_contexts":contexts,
            "references":ground_truth
        })


    performance = evaluate(
        dataset = HFDataset.from_list(records),
        metrics = [
            Faithfulness(llm=ragas_llm),
            AnswerRelevancy(llm=ragas_llm),
            ContextRecall(),
            ContextPrecision()
        ],
        embeddings = build_embedding()
    )

    df = performance.to_pandas()
    return df

if __name__ == "__main__":
    data = load_dataset()
    df = generate_rag_response(data)
    print(df)




