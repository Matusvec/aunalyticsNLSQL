import subprocess
import sys
import os

def main():
    print("Please enter your natural language query to convert to SQL:")
    user_query = input()
    
    # Get model from environment variable, default to phi (lightweight model)
    model = os.environ.get('OLLAMA_MODEL', 'phi')
    
    # Craft the prompt to instruct the model to act as a SQL generator
    prompt = f"You are a SQL query generator. Your task is to convert natural language requests into valid SQL queries. Respond with ONLY the SQL query, no explanations, greetings, or additional text. Generate the SQL query for: {user_query}"
    
    try:
        # Run ollama command with the question
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True,
            text=True,
            check=True
        )
        print("Generated SQL Query:")
        print(result.stdout.strip())
    except subprocess.CalledProcessError as e:
        print(f"Error running Ollama: {e}")
        print(f"Stderr: {e.stderr}")
        print("Make sure Ollama is installed, running, and the model is available.")
        sys.exit(1)
    except FileNotFoundError:
        print("Ollama command not found. Please install Ollama.")
        sys.exit(1)

if __name__ == "__main__":
    main() 