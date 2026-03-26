import sys

from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

# template for the ollama model to go by
template = """
You are a SQL Expert for a SQLite database. 
Your goal is to convert Natural Language into valid SQL queries.

SCHEMA CONTEXT:
Table: Users (id, name, signup_date)
Table: Orders (order_id, user_id, total_amount, status)

STRICT RULES:
1. Include EVERY column requested by the user in the SELECT clause.
2. If the user asks for "names and IDs," you must include both columns.
3. Use table aliases (e.g., 'u' for Users, 'o' for Orders) for readability.
4. If a JOIN is required, explicitly state the join condition.
5. Return ONLY the SQL code block. No conversational filler.

Example:
User: "Show user names and their order IDs"
Assistant: SELECT u.name, o.order_id FROM Users u JOIN Orders o ON u.id = o.user_id;

Here is the conversation history: {context}

Question: {question}

Answer:
"""
#
sys.stdout.reconfigure(encoding="utf-8")

model = OllamaLLM(model="gemma3")
prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

def handle_conversation():
    context = ""
    print("Welcome to the AI SQL ChatBot! Type 'exit' to quit.")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        result = chain.invoke({"context": context, "question": user_input})
        print("Bot: ", result)
        context += f"\nUser: {user_input}\nAI: {result}"


if __name__ == "__main__":
    handle_conversation()