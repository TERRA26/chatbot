# test_client.py
import requests
import json
import argparse
import time
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)


class ChatbotTestClient:
    def __init__(self, server_url):
        self.server_url = server_url

    def check_server_health(self):
        """Check if the server is running and get website info"""
        try:
            response = requests.get(f"{self.server_url}/health")

            if response.status_code == 200:
                data = response.json()
                print(f"{Fore.GREEN}Server is healthy!")
                print(f"{Fore.WHITE}Website: {data.get('website', 'Unknown')}")
                print(f"{Fore.WHITE}Context last updated: {data.get('context_last_updated', 'Unknown')}")
                return True
            else:
                print(f"{Fore.RED}Server returned status code: {response.status_code}")
                return False

        except Exception as e:
            print(f"{Fore.RED}Error connecting to server: {e}")
            return False

    def send_query(self, query):
        """Send a query to the chatbot"""
        print(f"\n{Fore.YELLOW}User: {query}")

        try:
            response = requests.post(
                f"{self.server_url}/api/query",
                json={"query": query}
            )

            data = response.json()

            if response.status_code == 200:
                print(f"{Fore.GREEN}Chatbot: {data.get('response', '')}")
                print(f"{Fore.BLUE}{data.get('source', '')}")
                return data
            else:
                print(f"{Fore.RED}Error: {data}")
                return None

        except Exception as e:
            print(f"{Fore.RED}Error connecting to server: {e}")
            return None

    def interactive_mode(self):
        """Run an interactive session with the chatbot"""
        print(f"{Fore.CYAN}=== Context-Aware Chatbot Test Client ===")
        print(f"{Fore.CYAN}Server: {self.server_url}")

        if not self.check_server_health():
            print(f"{Fore.RED}Server is not healthy. Exiting.")
            return

        print(f"{Fore.CYAN}Type 'exit' or 'quit' to end the session.")

        # Main interaction loop
        while True:
            query = input(f"\n{Fore.YELLOW}You: ")

            if query.lower() in ['exit', 'quit']:
                break

            if not query:
                continue

            self.send_query(query)

        print(f"{Fore.CYAN}=== Session Ended ===")


def main():
    parser = argparse.ArgumentParser(description="Test client for the Context-Aware Website Chatbot")
    parser.add_argument("--server", default="http://localhost:8000", help="Server URL (default: http://localhost:8000)")
    parser.add_argument("--query", help="Query to send (bypasses interactive mode)")

    args = parser.parse_args()

    client = ChatbotTestClient(args.server)

    if args.query:
        # Non-interactive mode
        if client.check_server_health():
            client.send_query(args.query)
    else:
        # Interactive mode
        client.interactive_mode()


if __name__ == "__main__":
    main()