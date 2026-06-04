import os
import sys

# Ensure agent package is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools.web_skills import web_search

def main():
    print("Testing Bing Search via Playwright...")
    result = web_search("Python 3.14 release date", max_results=3)
    print("="*40)
    print(result)
    print("="*40)
    
if __name__ == "__main__":
    main()
