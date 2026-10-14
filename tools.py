import requests
from langchain_core.tools import Tool
from langchain_core.tools import StructuredTool
from langchain_community.tools import DuckDuckGoSearchRun

def wikipedia_search(query: str):
    # Step 1: Search Wikipedia
    search_response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 3
        },
        headers={
            "User-Agent": "ResearchAgent/1.0"
        },
        timeout=50
    )

    search_response.raise_for_status()

    search_data = search_response.json()

    results = search_data.get("query", {}).get("search", [])

    if not results:
        return "No Wikipedia results found."

    # Step 2: Get detailed summaries
    detailed_results = []

    for result in results:
        title = result["title"]

        page_response = requests.get(
            "https://en.wikipedia.org/api/rest_v1/page/summary/"
            + requests.utils.quote(title),
            headers={
                "User-Agent": "ResearchAgent/1.0"
            },
            timeout=50
        )

        page_response.raise_for_status()

        page_data = page_response.json()

        description = page_data.get(
            "extract",
            "No detailed description available."
        )

        detailed_results.append(
            f"Title: {title}\n"
            f"Description: {description}"
        )

    # Step 3: Return clean text to the agent
    return "\n\n".join(detailed_results)

    response.raise_for_status()

    data = response.json()

    results = data.get("query", {}).get("search", [])

    if not results:
        return "No Wikipedia results found."

    return "\n\n".join(
        f"Title: {result['title']}\n"
        f"Summary: {result['snippet']}"
        for result in results
    )


wikipedia_tool = Tool(
    name="wikipedia",
    func=wikipedia_search,
    description="Search Wikipedia for reliable research information."
)


search = DuckDuckGoSearchRun()
search_tool = Tool(
    name="search",
    func=search.run,
    description="Search the web for current information."
)