import argparse
import os
from pathlib import Path
from langchain import hub
from langchain_community.document_loaders import PyPDFLoader, UnstructuredHTMLLoader
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import START, StateGraph
from typing_extensions import TypedDict
from API_keys import TDarkRAG_API_key, LANGCHAIN_TRACING_V2, LANGCHAIN_ENDPOINT, LANGCHAIN_API_KEY, LANGCHAIN_PROJECT

# Set API keys as environment variables
os.environ["OPENAI_API_KEY"] = TDarkRAG_API_key
os.environ["LANGCHAIN_TRACING_V2"] = LANGCHAIN_TRACING_V2
os.environ["LANGCHAIN_ENDPOINT"] = LANGCHAIN_ENDPOINT
os.environ["LANGCHAIN_API_KEY"] = LANGCHAIN_API_KEY
os.environ["LANGCHAIN_PROJECT"] = LANGCHAIN_PROJECT


def load_documents_from_folder(folder_path: str):
    documents = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if filename.endswith('.pdf'):
            loader = PyPDFLoader(file_path)
            documents.extend(loader.load())
        elif filename.endswith('.html'):
            loader = UnstructuredHTMLLoader(file_path)
            documents.extend(loader.load())
        else:
            print(f"Unsupported format: {filename}")
    return documents


def save_response_to_file(output_dir, question, answer):
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)
    sanitized_filename = "".join(c if c.isalnum() or c in " _-" else "_" for c in question) + ".md"
    file_path = output_dir / sanitized_filename
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(f"# Wikipedia page\n{answer}")
    print(f"Response saved to {file_path}")
    return str(file_path)


def main(input_dir, output_dir, question, llm_model, embeddings_model, vector_store_type="InMemory"):
    # LLM and embedding models to be used
    llm = ChatOpenAI(model=llm_model)
    embeddings = OpenAIEmbeddings(model=embeddings_model)

    # Define the type of the vector store
    if vector_store_type == "InMemory":
        vector_store = InMemoryVectorStore(embeddings)
    else:
        raise ValueError(f"Unknown vector store type: {vector_store_type}")

    docs_path = Path(input_dir)
    all_documents = load_documents_from_folder(docs_path)

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200, add_start_index=True)
    all_splits = text_splitter.split_documents(all_documents)
    vector_store.add_documents(documents=all_splits)

    prompt = hub.pull("tdarkrag-wikipedia-page-generation")

    class State(TypedDict):
        question: str
        context: list[Document]
        answer: str

    def retrieve(state: State):
        retriever = vector_store.as_retriever(searh_type="similarity", k=100)
        retrieved_docs = retriever.get_relevant_documents(state["question"])
        return {"context": retrieved_docs}

    def generate(state: State):
        docs_content = "\n\n".join(
            f"source: {doc.metadata['source']}\nchunk: {doc.page_content}" for doc in state["context"])
        message_for_llm = prompt.invoke(
            {"target_audience": "Biologists and people with a degree in medicine.", "context": docs_content})
        response = llm.invoke(message_for_llm)
        file_path = save_response_to_file(output_dir, state["question"], response.content)
        return {"answer": response.content, "output_path": file_path}

    graph_builder = StateGraph(State).add_sequence([retrieve, generate])
    graph_builder.add_edge(START, "retrieve")
    graph = graph_builder.compile()

    state = {"question": question}
    output_path = None
    for step in graph.stream(state, stream_mode="updates"):
        print(f"{step}\n\n----------------\n")
        if "output_path" in step:
            output_path = step["output_path"]
            break

    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a Wikipedia page from documents in a folder.")
    parser.add_argument("--input_dir", required=True, help="Path to the folder containing documents.")
    parser.add_argument("--output_dir", required=True, help="Path to the output folder.")
    parser.add_argument("--question", required=True, help="Question to answer.")
    parser.add_argument("--llm_model", default="gpt-4o-mini", help="LLM model to use.")
    parser.add_argument("--embeddings_model", default="text-embedding-3-large", help="Embeddings model to use.")
    parser.add_argument("--vector_store_type", default="InMemory", help="Type of vector store to use.")
    args = parser.parse_args()

    main(args.input_dir, args.output_dir, args.question, args.llm_model, args.embeddings_model, args.vector_store_type)
