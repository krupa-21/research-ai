from datetime import datetime
import json
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from pydantic import BaseModel
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor

from tools import search_tool, wikipedia_tool


# ---------------------------------------------------------
# Flask application
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)


# ---------------------------------------------------------
# AI / Agent configuration
# ---------------------------------------------------------

llm = ChatOllama(
    model="qwen2.5:3b",
    temperature=0,
)


class ResearchResponse(BaseModel):
    topic: str
    summary: str
    sources: list[str]
    tools_used: list[str]


parser = PydanticOutputParser(pydantic_object=ResearchResponse)

prompt = ChatPromptTemplate.from_messages([
    (
         "system",
"""
You are a professional research assistant.

Your role is to research the user's query using the available tools,
analyze the information collected, and produce a detailed and
well-written research paper.

Your behavior should be professional, accurate, objective, and
research-oriented. Use the available tools when they are useful.
Base your research on the information returned by those tools and do
not invent unsupported facts.

After completing the research, synthesize the information into a
professional, detailed research paper.

The research paper should be properly structured and should read like
a real research paper rather than a short chatbot answer.

Use an appropriate structure for the topic, such as:

Introduction

Main discussion with relevant sections and sub-sections

Important findings, characteristics, history, applications,
significance, advantages, limitations, or other relevant aspects

Conclusion

Choose the sections naturally according to the topic. Do not include
irrelevant sections.

For multiple topics, clearly separate and explain each topic and
include a comparison or relationship section when appropriate.

The final response must also clearly provide:
- The research topic
- The detailed research paper
- The actual sources used
- The actual tools used during the research

Do not invent sources or claim that a tool was used if it was not used.

Do not copy raw tool output directly. Synthesize and organize it into
a coherent research paper.

Do not include raw HTML or phrases such as
<span class="searchmatch"> from search results.

The final response MUST follow the provided output format:

{format_instructions}
"""
    ),
    ("placeholder", "{chat_history}"),
    ("human", "{query}"),
    ("placeholder", "{agent_scratchpad}"),
]).partial(format_instructions=parser.get_format_instructions())
tools = [search_tool, wikipedia_tool]

agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=tools,
)

agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def parse_agent_output(output):
    """Convert the agent's structured output into a ResearchResponse."""
    if isinstance(output, ResearchResponse):
        return output

    if isinstance(output, dict):
        try:
            return ResearchResponse.model_validate(output)
        except Exception:
            pass

    text = str(output).strip()

    # Try normal JSON first.
    try:
        return ResearchResponse.model_validate(json.loads(text))
    except Exception:
        pass

    # Try JSON inside a Markdown code fence.
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return ResearchResponse.model_validate(json.loads(fenced.group(1)))
        except Exception:
            pass

    # Last-resort fallback so the website still receives a usable result.
    return ResearchResponse(
        topic="Research Result",
        summary=text,
        sources=[],
        tools_used=[],
    )


def save_research(research: ResearchResponse):
    """Append a research paper to research_output.txt."""
    output_file = BASE_DIR / "research_output.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with output_file.open("a", encoding="utf-8") as file:
        file.write("\n")
        file.write("=" * 80 + "\n")
        file.write("                    RESEARCH PAPER\n")
        file.write("=" * 80 + "\n\n")
        file.write(f"Date & Time: {timestamp}\n")
        file.write(f"Topic: {research.topic}\n\n")
        file.write(research.summary)
        file.write("\n\nSources:\n")

        if research.sources:
            for source in research.sources:
                file.write(f"- {source}\n")
        else:
            file.write("- No source list returned by the agent.\n")

        file.write("\nTools Used:\n")

        if research.tools_used:
            for tool in research.tools_used:
                file.write(f"- {tool}\n")
        else:
            file.write("- No tool list returned by the agent.\n")

        file.write("\n" + "=" * 80 + "\n")
        file.write("                 END OF RESEARCH PAPER\n")
        file.write("=" * 80 + "\n\n")

    return output_file


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

@app.route("/")
def home():
    # index.html can stay beside main2.py; no templates folder required.
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "message": "Research AI backend is running.",
            "model": "qwen2.5:3b",
        }
    )


@app.route("/research", methods=["POST"])
def research():
    data = request.get_json(silent=True) or request.form
    topic = str(data.get("topic", "")).strip()

    if not topic:
        return jsonify({"success": False, "error": "Please enter a research topic."}), 400

    if len(topic) > 500:
        return jsonify(
            {"success": False, "error": "Research topic is too long. Keep it under 500 characters."}
        ), 400

    try:
        raw_response = agent_executor.invoke(
            {
                "query": topic,
                "chat_history": [],
            }
        )

        research_result = parse_agent_output(raw_response.get("output", ""))

        return jsonify(
            {
                "success": True,
                "research": research_result.model_dump(),
            }
        )

    except Exception as exc:
        app.logger.exception("Research request failed")
        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


@app.route("/save", methods=["POST"])
def save():
    data = request.get_json(silent=True) or {}

    try:
        research_result = ResearchResponse.model_validate(data.get("research", {}))
    except Exception:
        return jsonify(
            {"success": False, "error": "Invalid research data."}
        ), 400

    try:
        output_file = save_research(research_result)

        return jsonify(
            {
                "success": True,
                "message": "Research successfully saved.",
                "filename": output_file.name,
            }
        )

    except Exception as exc:
        app.logger.exception("Saving research failed")
        return jsonify(
            {
                "success": False,
                "error": str(exc),
            }
        ), 500


# ---------------------------------------------------------
# Run server
# ---------------------------------------------------------

if __name__ == "__main__":
    print("\nResearch AI server starting...")
    print("Open: http://127.0.0.1:5000")
    print("Make sure Ollama is running and qwen2.5:3b is installed.\n")

    app.run(host="127.0.0.1", port=5000, debug=True)