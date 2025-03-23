import logging
from langchain.prompts import PromptTemplate
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from langchain.vectorstores.chroma import Chroma
from langchain.embeddings.openai import OpenAIEmbeddings

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_conversational_chain(openai_api_key, local_persist_path, model_name="gpt-4"):
    """Create conversational retrieval chain for the document database."""
    try:
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)
        
        # Load ChromaDB
        db = Chroma(persist_directory=local_persist_path, embedding_function=embeddings)
        retriever = db.as_retriever(search_type="similarity", search_kwargs={"k": 3})
        
        # Initialize memory
        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True, output_key='answer')
        
        # Create prompt template
        template = """
        You are a helpful AI assistant. You're tasked to answer the question given below, but only based on the context provided.
        
        context:
        {context}
        
        question:
        {input}
        
        If you cannot find an answer, ask the user to rephrase the question.
        answer:
        """
        prompt = PromptTemplate.from_template(template)
        
        # Initialize LLM
        llm_openai = ChatOpenAI(model=model_name, openai_api_key=openai_api_key, temperature=0)
        
        # Create retrieval chain
        conversational_retrieval = ConversationalRetrievalChain.from_llm(
            llm=llm_openai, 
            retriever=retriever, 
            memory=memory, 
            verbose=False
        )
        
        return conversational_retrieval
        
    except Exception as e:
        logger.error(f"Error creating conversational chain: {str(e)}")
        return None

def get_response(chain, question):
    """Get a response from the conversational chain."""
    try:
        response = chain({"question": question})
        return response["answer"]
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        return f"Error generating response: {str(e)}"