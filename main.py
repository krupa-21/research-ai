import io
import os
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_file, send_from_directory
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor

from pdf_export import build_pdf
from tools import search_tool, wikipedia_tool


# ---------------------------------------------------------
# Flask application
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
REPORTS_DIR = BASE_DIR / "reports"

app = Flask(__name__)


# ---------------------------------------------------------
# Models
#
# Both versions use the same model by default. To get a true
# "two different LLMs" comparison, pull a second model with
# Ollama and start the app with MODEL_B set, e.g.:
#
#   PowerShell:  $env:MODEL_B="llama3.2:3b"; python main.py
#   CMD:         set MODEL_B=llama3.2:3b && python main.py
#
# The second model must support plain chat (no tool calling is
# needed for Version B).
# ---------------------------------------------------------

MODEL_A = os.getenv("MODEL_A", "qwen2.5:3b")
MODEL_B = os.getenv("MODEL_B", MODEL_A)

llm_a = ChatOllama(
    model=MODEL_A,
    temperature=0,
)

llm_b = ChatOllama(
    model=MODEL_B,
    temperature=0.4,
)


# ---------------------------------------------------------
# Version A: detailed research paper (agent that uses tools)
# ---------------------------------------------------------

paper_prompt = ChatPromptTemplate.from_messages([
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
# Version B: short executive brief
#
# Written from the same research notes the agent collected
# for Version A, so the web is only searched once. The prompt
# asks for a different structure and tone, so the two
# versions are genuinely different documents.
# ---------------------------------------------------------

brief_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """
You are a research analyst writing a concise executive brief for a
busy, non-expert reader.

You are given a topic and research notes gathered from search tools.
Base the brief on those notes. If the notes are empty or unhelpful,
write only what you are confident is true and say that the evidence
was limited. Do not invent unsupported facts, numbers or quotes.

Write the brief in Markdown with exactly this structure:

# Overview
Two or three sentences explaining the topic in plain language.

# Key Takeaways
Four to six bullet points. Each is one clear sentence.

# Why It Matters
One short paragraph on real-world relevance.

# Risks and Open Questions
Two to four bullet points.

# Bottom Line
One or two sentences.

Keep the whole brief under about 450 words.
Use plain, direct language. No jargon without explanation.

IMPORTANT:
Return ONLY the brief.
Do NOT return JSON.
Do NOT mention these instructions.
Do NOT copy the raw research notes.
"""
    ),
    (
        "human",
        "Topic: {topic}\n\nResearch notes:\n{notes}"
    ),
])

brief_chain = brief_prompt | llm_b


# ---------------------------------------------------------
# Tools and agent (Version A)
# ---------------------------------------------------------

tools = [
    search_tool,
    wikipedia_tool,
]

agent = create_tool_calling_agent(
    llm=llm_a,
    prompt=paper_prompt,
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

    # Strip punctuation that is not part of the URL
    urls = [u.rstrip(".,;:)") for u in urls]

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
# Helper: collect sources and notes from the tool output
# ---------------------------------------------------------

def get_sources(intermediate_steps):

    sources = []

    for step in intermediate_steps or []:
        try:
            for url in extract_urls(str(step[1])):
                if url not in sources:
                    sources.append(url)
        except Exception:
            continue

    return sources


def get_notes(intermediate_steps, limit=6000):
    """
    Join the raw tool output into one block of research notes
    for Version B. Truncated so a small local model can cope.
    """

    parts = []

    for step in intermediate_steps or []:
        try:
            parts.append(str(step[1]).strip())
        except Exception:
            continue

    notes = "\n\n".join(p for p in parts if p)

    return notes[:limit]


# ---------------------------------------------------------
# Helper: file names
# ---------------------------------------------------------

def slugify(text, fallback="report", max_length=50):

    slug = re.sub(r"[^A-Za-z0-9]+", "-", str(text or "")).strip("-").lower()

    return slug[:max_length].strip("-") or fallback


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

    model_text = MODEL_A if MODEL_A == MODEL_B else f"{MODEL_A} + {MODEL_B}"

    return jsonify({
        "status": "ok",
        "message": "Research AI backend is running.",
        "model": model_text,
    })


# ---------------------------------------------------------
# Research
#
# Returns TWO versions of the report:
#   A - detailed research paper (agent + tools)
#   B - short executive brief
#
# If one version fails the other is still returned.
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

    print("\n")
    print("=" * 80)
    print("STARTING RESEARCH")
    print("=" * 80)
    print(f"Topic: {topic}")
    print("=" * 80)

    versions = []
    intermediate_steps = []

    # -----------------------------------------------------
    # Version A: detailed paper (runs the tools)
    # -----------------------------------------------------

    version_a = {
        "id": "A",
        "label": "Version A: Detailed Paper",
        "description": "In-depth research paper written by the tool-using agent.",
        "model": MODEL_A,
        "content": "",
        "sources": [],
        "tools_used": [],
        "error": None,
    }

    try:

        raw_response = agent_executor.invoke({
            "query": topic,
            "chat_history": [],
        })

        paper = str(raw_response.get("output", "")).strip()

        if not paper:
            raise RuntimeError("The research agent returned an empty response.")

        intermediate_steps = raw_response.get("intermediate_steps", [])

        version_a["content"] = paper
        version_a["tools_used"] = get_tools_used(intermediate_steps)
        version_a["sources"] = get_sources(intermediate_steps)

    except Exception as exc:

        app.logger.exception("Version A failed")

        version_a["error"] = str(exc) or "Version A failed."

    versions.append(version_a)

    # -----------------------------------------------------
    # Version B: executive brief (from the same notes)
    # -----------------------------------------------------

    version_b = {
        "id": "B",
        "label": "Version B: Executive Brief",
        "description": "Short, plain-language summary of the same research.",
        "model": MODEL_B,
        "content": "",
        "sources": list(version_a["sources"]),
        "tools_used": list(version_a["tools_used"]),
        "error": None,
    }

    try:

        notes = get_notes(intermediate_steps) or "(No research notes were collected.)"

        brief_response = brief_chain.invoke({
            "topic": topic,
            "notes": notes,
        })

        brief = str(getattr(brief_response, "content", brief_response)).strip()

        if not brief:
            raise RuntimeError("The model returned an empty brief.")

        version_b["content"] = brief

    except Exception as exc:

        app.logger.exception("Version B failed")

        version_b["error"] = str(exc) or "Version B failed."

    versions.append(version_b)

    # -----------------------------------------------------
    # Result
    # -----------------------------------------------------

    print("\n")
    print("=" * 80)
    for version in versions:
        status = "ERROR: " + version["error"] if version["error"] else "OK"
        print(f"{version['label']}: {status}")
        print(f"  tools: {version['tools_used']}")
        print(f"  sources: {len(version['sources'])}")
    print("=" * 80)

    if all(v["error"] for v in versions):

        return jsonify({
            "success": False,
            "error": version_a["error"],
        }), 500

    return jsonify({
        "success": True,
        "research": {
            "topic": topic,
            "versions": versions,
        }
    })


# ---------------------------------------------------------
# Download / save as PDF
#
# The browser sends the version the user picked; the server
# builds a PDF, keeps a copy in the reports/ folder and sends
# the PDF back as a download.
# ---------------------------------------------------------

@app.route("/download-pdf", methods=["POST"])
def download_pdf():

    data = request.get_json(silent=True) or {}

    topic = str(data.get("topic") or "Research Report").strip()
    content = str(data.get("content") or "")
    version_label = str(data.get("version_label") or "")
    model = str(data.get("model") or "")

    sources = data.get("sources") or []
    tools_used = data.get("tools_used") or []

    if not isinstance(sources, list):
        sources = []

    if not isinstance(tools_used, list):
        tools_used = []

    if not content.strip():

        return jsonify({
            "success": False,
            "error": "No research content to save."
        }), 400

    if len(content) > 200_000:

        return jsonify({
            "success": False,
            "error": "Research content is too large to export."
        }), 400

    try:

        pdf_bytes = build_pdf(
            topic=topic,
            content=content,
            sources=[str(s) for s in sources],
            tools_used=[str(t) for t in tools_used],
            version_label=version_label,
            model=model,
        )

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

        version_tag = slugify(version_label.split(":")[0], fallback="report")

        filename = f"{slugify(topic)}-{version_tag}-{timestamp}.pdf"

        # Keep a copy on disk as well (best effort)
        try:
            REPORTS_DIR.mkdir(exist_ok=True)
            (REPORTS_DIR / filename).write_bytes(pdf_bytes)
        except OSError:
            app.logger.warning("Could not save a copy in %s", REPORTS_DIR)

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as exc:

        app.logger.exception("PDF export failed")

        return jsonify({
            "success": False,
            "error": f"Could not create the PDF: {exc}",
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
        f"Make sure Ollama is running and {MODEL_A}"
        + ("" if MODEL_A == MODEL_B else f" and {MODEL_B}")
        + " installed.\n"
    )

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )