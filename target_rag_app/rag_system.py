import os
from dotenv import load_dotenv

# V-- UPDATE IMPORTS FOR FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS # Use FAISS instead of Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA

def create_rag_chain():
    """
    Builds and returns a Retrieval-Augmented Generation chain powered by Gemini using FAISS.
    """
    load_dotenv()
    
    with open('data/private_data.txt', 'r', encoding='utf-8') as f:
        private_text = f.read()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=40,
        length_function=len
    )
    docs = text_splitter.create_documents([private_text])
    print(f"[Target RAG] Split document into {len(docs)} chunks.")

    embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")
    
    # --- START OF FAISS IMPLEMENTATION ---
    db_file_path = "faiss_index"

    if os.path.exists(db_file_path):
        # Load the existing FAISS index
        vectorstore = FAISS.load_local(db_file_path, embedding_function, allow_dangerous_deserialization=True)
        print("[Target RAG] Loaded existing FAISS index.")
    else:
        # Create and save a new FAISS index
        print("[Target RAG] Creating new FAISS index. This may take a moment...")
        vectorstore = FAISS.from_documents(docs, embedding_function)
        vectorstore.save_local(db_file_path)
        print(f"[Target RAG] Saved new FAISS index to '{db_file_path}'")
    # --- END OF FAISS IMPLEMENTATION ---


    llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.7,
        convert_system_message_to_human=True
    )
    print("[Target RAG] Initialized Gemini Pro model.")

    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    
    rag_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        return_source_documents=True
    )
    print("[Target RAG] RAG chain created successfully.")
    
    return rag_chain

if __name__ == '__main__':
    chain = create_rag_chain()
    response = chain({"query": "What is Project Raven?"})
    print("\n--- Test Query Response ---")
    print(response['result'])
    print("---------------------------\n")