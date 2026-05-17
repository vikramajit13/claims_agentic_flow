from typing import Annotated
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages

# 1. Define the Shared Graph State
class State(TypedDict):
    # add_messages appends new LLM responses to the conversation history
    messages: Annotated[list, add_messages]

# 2. Initialize the LLM Client
# Ensure your OPENAI_API_KEY environment variable is set
llm_client = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

# 3. Define the Node Function to Invoke the LLM
def invoke_llm_node(state: State):
    # Pass the current message history to the LLM client
    response = llm_client.invoke(state["messages"])
    
    # Return the new message to update the state
    return {"messages": [response]}