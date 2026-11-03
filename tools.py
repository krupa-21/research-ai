from urllib.parse import quote

import requests
from langchain_core.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun


HEADERS = {"User-Agent": "ResearchAgent/1.0"}


def wikipedia_search(query: str) -> str:
    """Search Wikipedia and return titles, summaries and page URLs as text."""

    try:
        # Step 1: search Wikipedia
        search_response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 3,
            },
            headers=HEADERS,
            timeout=50,
        )
        search_response.raise_for_status()

        results = search_response.json().get("query", {}).get("search", [])

    except Exception as exc:
        # Return the problem as text so the agent can carry on
        # instead of the whole research request crashing.
        return f"Wikipedia search failed: {exc}"

    if not results:
        return "No Wikipedia results found."

    # Step 2: get a detailed summary for every result
    detailed_results = []

    for result in results:
        title = result["title"]
        page_url = (
            "https://en.wikipedia.org/wiki/"
            + quote(title.replace(" ", "_"), safe="")
        )
        description = "No detailed description available."

        try:
            page_response = requests.get(
                "https://en.wikipedia.org/api/rest_v1/page/summary/"
                + quote(title, safe=""),
                headers=HEADERS,
                timeout=50,
            )
            page_response.raise_for_status()
            page_data = page_response.json()

            description = page_data.get("extract") or description

            page_url = (
                page_data.get("content_urls", {})
                .get("desktop", {})
                .get("page", page_url)
            )

        except Exception:
            # One failing page should not throw away the other results.
            pass

        # The URL is included so that main.py can list it as a source.
        detailed_results.append(
            f"Title: {title}\n"
            f"URL: {page_url}\n"
            f"Description: {description}"
        )

    # Step 3: return clean text to the agent
    return "\n\n".join(detailed_results)


wikipedia_tool = Tool(
    name="wikipedia",
    func=wikipedia_search,
    description="Search Wikipedia for reliable research information.",
)


_search = DuckDuckGoSearchRun()


def safe_web_search(query: str) -> str:
    """DuckDuckGo search that reports errors (e.g. rate limits) as text."""

    try:
        return _search.run(query)
    except Exception as exc:
        return f"Web search failed: {exc}"


search_tool = Tool(
    name="search",
    func=safe_web_search,
    description="Search the web for current information.",
)