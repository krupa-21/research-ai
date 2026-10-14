from datetime import datetime
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
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


# ---------------------------------------------------------
# Agent prompt
# ---------------------------------------------------------

prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a professional research assistant.

Your job is to research the user's query using the available tools,
analyze the information returned by those tools, and produce a
detailed, accurate and well-structured research paper.

Use the available tools whenever they are useful.

Base your research on information returned by the tools.
Do not invent unsupported facts.

The final answer should be a professional research paper, not a
short chatbot response.

Structure the research naturally according to the topic.

For example, when appropriate, use:

# Introduction

# Main Discussion

## Relevant Subtopics

# Important Findings

# Significance / Applications

# Limitations / Challenges

# Conclusion

Do NOT force sections that are irrelevant to the topic.

For multiple topics, clearly separate them and include a comparison
or relationship section when appropriate.

IMPORTANT:

Return ONLY the actual research paper.

Do NOT return JSON.

Do NOT return Python dictionaries.

Do NOT return a Pydantic schema.

Do NOT return format instructions.

Do NOT explain how you generated the answer.

Do NOT include raw tool output.

Synthesize the information from the tools into a coherent research
paper using Markdown headings, paragraphs and bullet points where
appropriate.
"""
    ),
    ("placeholder", "{chat_history}"),
    ("human", "{query}"),
    ("placeholder", "{agent_scratchpad}"),
])


# ---------------------------------------------------------
# Tools
# ---------------------------------------------------------

tools = [
    search_tool,
    wikipedia_tool,
]


# ---------------------------------------------------------
# Create agent
# ---------------------------------------------------------

agent = create_tool_calling_agent(
    llm=llm,
    prompt=prompt,
    tools=tools,
)


agent_executor = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,

    # IMPORTANT:
    # This allows us to see which tools LangChain actually used.
    return_intermediate_steps=True,
)


# ---------------------------------------------------------
# Helper: extract URLs from tool output
# ---------------------------------------------------------

def extract_urls(text):
    """
    Extract URLs from tool output.

    This does NOT parse the AI's research paper.
    It only looks at the actual tool responses.
    """

    if not text:
        return []

    urls = re.findall(
        r"https?://[^\s\]\[<>\"']+",
        str(text)
    )

    # Remove duplicates while preserving order
    return list(dict.fromkeys(urls))


# ---------------------------------------------------------
# Helper: get actual tools used
# ---------------------------------------------------------

def get_tools_used(intermediate_steps):
    """
    Get the names of tools actually invoked by the agent.
    """

    tools_used = []

    for step in intermediate_steps or []:
        try:
            action = step[0]

            tool_name = getattr(action, "tool", None)

            if tool_name and tool_name not in tools_used:
                tools_used.append(tool_name)

        except Exception:
            continue

    return tools_used


# ---------------------------------------------------------
# Save research
# ---------------------------------------------------------

def save_research(topic, research, sources, tools_used):

    output_file = BASE_DIR / "research_output.txt"

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with output_file.open("a", encoding="utf-8") as file:

        file.write("\n")
        file.write("=" * 80 + "\n")
        file.write("                    RESEARCH PAPER\n")
        file.write("=" * 80 + "\n\n")

        file.write(f"Date & Time: {timestamp}\n")
        file.write(f"Topic: {topic}\n\n")

        file.write(research)

        file.write("\n\nSources:\n")

        if sources:
            for source in sources:
                file.write(f"- {source}\n")
        else:
            file.write("- No URL sources returned by the tools.\n")

        file.write("\nTools Used:\n")

        if tools_used:
            for tool in tools_used:
                file.write(f"- {tool}\n")
        else:
            file.write("- No tools reported.\n")

        file.write("\n")
        file.write("=" * 80 + "\n")
        file.write("                END OF RESEARCH PAPER\n")
        file.write("=" * 80 + "\n\n")

    return output_file


# ---------------------------------------------------------
# Home
# ---------------------------------------------------------

@app.route("/")
def home():

    return send_from_directory(
        BASE_DIR,
        "index.html"
    )


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.route("/api/health", methods=["GET"])
def health():

    return jsonify({
        "status": "ok",
        "message": "Research AI backend is running.",
        "model": "qwen2.5:3b",
    })


# ---------------------------------------------------------
# Research
# ---------------------------------------------------------

@app.route("/research", methods=["POST"])
def research():

    data = request.get_json(silent=True) or request.form

    topic = str(
        data.get("topic", "")
    ).strip()

    if not topic:

        return jsonify({
            "success": False,
            "error": "Please enter a research topic."
        }), 400

    if len(topic) > 500:

        return jsonify({
            "success": False,
            "error": "Research topic is too long. Keep it under 500 characters."
        }), 400

    try:

        print("\n")
        print("=" * 80)
        print("STARTING RESEARCH")
        print("=" * 80)
        print(f"Topic: {topic}")
        print("=" * 80)

        # -------------------------------------------------
        # Run agent
        # -------------------------------------------------

        raw_response = agent_executor.invoke({
            "query": topic,
            "chat_history": [],
        })

        # -------------------------------------------------
        # IMPORTANT:
        # Take exactly what the AI generated.
        # No Pydantic parsing.
        # No JSON parsing.
        # -------------------------------------------------

        research_output = str(
            raw_response.get("output", "")
        ).strip()

        if not research_output:

            raise Exception(
                "The research agent returned an empty response."
            )

        # -------------------------------------------------
        # Get actual tools used
        # -------------------------------------------------

        intermediate_steps = raw_response.get(
            "intermediate_steps",
            []
        )

        tools_used = get_tools_used(
            intermediate_steps
        )

        # -------------------------------------------------
        # Get URLs from actual tool output
        # -------------------------------------------------

        sources = []

        for step in intermediate_steps:

            try:

                tool_output = step[1]

                urls = extract_urls(
                    str(tool_output)
                )

                for url in urls:

                    if url not in sources:
                        sources.append(url)

            except Exception:
                continue

        # -------------------------------------------------
        # Debug information
        # -------------------------------------------------

        print("\n")
        print("=" * 80)
        print("FINAL AI OUTPUT")
        print("=" * 80)

        print(research_output)

        print("\n")
        print("=" * 80)
        print("TOOLS USED")
        print("=" * 80)

        print(tools_used)

        print("\n")
        print("=" * 80)
        print("SOURCES")
        print("=" * 80)

        print(sources)

        print("\n")
        print("=" * 80)
        print("RESEARCH COMPLETE")
        print("=" * 80)

        # -------------------------------------------------
        # Return directly to frontend
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "research": {

                "topic": topic,

                # THIS IS THE ACTUAL AI OUTPUT
                "content": research_output,

                "sources": sources,

                "tools_used": tools_used,
            }

        })

    except Exception as exc:

        app.logger.exception(
            "Research request failed"
        )

        return jsonify({

            "success": False,

            "error": str(exc),

        }), 500


# ---------------------------------------------------------
# Save
# ---------------------------------------------------------

@app.route("/save", methods=["POST"])
def save():

    data = request.get_json(
        silent=True
    ) or {}

    research_data = data.get(
        "research",
        {}
    )

    topic = str(
        research_data.get(
            "topic",
            "Research"
        )
    )

    content = str(
        research_data.get(
            "content",
            ""
        )
    )

    sources = research_data.get(
        "sources",
        []
    )

    tools_used = research_data.get(
        "tools_used",
        []
    )

    if not content.strip():

        return jsonify({

            "success": False,

            "error": "No research content to save."

        }), 400

    try:

        output_file = save_research(
            topic,
            content,
            sources,
            tools_used
        )

        return jsonify({

            "success": True,

            "message": "Research successfully saved.",

            "filename": output_file.name,

        })

    except Exception as exc:

        app.logger.exception(
            "Saving research failed"
        )

        return jsonify({

            "success": False,

            "error": str(exc),

        }), 500


# ---------------------------------------------------------
# Run server
# ---------------------------------------------------------

if __name__ == "__main__":

    print("\nResearch AI server starting...")

    print(
        "Open: http://127.0.0.1:5000"
    )

    print(
        "Make sure Ollama is running and qwen2.5:3b is installed.\n"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )