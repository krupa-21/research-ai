# Research AI

Research AI is a locally run, AI-assisted research paper generation application. It combines a browser-based interface with a Flask backend, a locally hosted language model through Ollama, and research tools for gathering and synthesizing information.

Users submit a research topic through the web interface. The research agent can use the configured search and Wikipedia tools, then generates a structured research-paper-style response. Each topic produces **two versions** of the report (a detailed research paper and a short executive brief). The interface shows both in tabs, along with source/tool information, and the user can download whichever version they prefer as a **PDF**.

## Features

- Accepts natural-language research topics.
- Generates structured, research-paper-style responses.
- Produces two different versions for every topic: **Version A** (detailed paper, written by the tool-using agent) and **Version B** (concise executive brief written from the same research notes). Optionally Version B can use a second LLM (see below).
- Runs the language model locally through Ollama using `qwen2.5:3b`.
- Uses LangChain to coordinate the model and configured research tools.
- Integrates web-search and Wikipedia tools defined in `tools.py`.
- Provides a browser-based interface for submitting topics and reading results.
- Displays source URLs and tools reported for the research run.
- **Save Report / Download PDF**: exports the selected version as a formatted PDF (title, headings, lists, sources, tools used). A copy is also kept in the `reports/` folder.
- Includes a backend health check and terminal logging.

## Technology Stack

| Component              | Technology                                                 |
| ---------------------- | ---------------------------------------------------------- |
| Frontend               | HTML, CSS, JavaScript                                      |
| Backend                | Python, Flask                                              |
| Language-model runtime | Ollama                                                     |
| Language model         | Qwen2.5:3B                                                 |
| Agent orchestration    | LangChain                                                  |
| Research tools         | Search and Wikipedia integrations configured in `tools.py` |

## Project Structure

The current project directory is organized as follows:

```text
ai-agent/
├── main.py                 # Main Flask application and research agent
├── backupmain.py           # Backup copy of the backend; not used to start the app
├── tools.py                # Research tool definitions
├── pdf_export.py           # Builds the PDF report (ReportLab)
├── reports/                # PDFs saved by the app (created automatically)
├── index.html              # Web interface served by Flask
├── templates/               # Existing folder; retain if used by your code
├── requirements.txt        # Python dependencies
├── .env                    # Local environment configuration, if needed
├── .gitignore              # Files excluded from Git
├── venv/                   # Local Python virtual environment; do not commit
└── README.md               # Project documentation
```

The `venv/`, `__pycache__/`, `.env`, and `reports/` entries are local/runtime files and should not be uploaded to a public repository. `backupmain.py` is retained as a backup; run `main.py` for the application.

## Prerequisites

- Python 3.11 or 3.12 (recommended).
- Ollama.
- Git, if you plan to clone or contribute to the repository.
- A modern web browser.
- Internet access for the configured online research tools.

## Installation and Setup

### 1. Get the project

Clone the repository:

```powershell
git clone <YOUR-REPOSITORY-URL>
cd ai-agent
```

If the project is already on your computer, open its existing folder in VS Code instead. Use the actual folder name if it differs from `ai-agent`.

### 2. Create and activate a virtual environment

If you already have a working `venv` folder, activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

If you need to create a new environment, run:

```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use Command Prompt:

```bat
venv\Scripts\activate.bat
```

Use a supported Python version installed on your computer. The virtual environment is local to your machine and should not be committed to Git.

### 3. Install Python dependencies

Install the packages listed in the project's existing `requirements.txt`:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Make sure `requirements.txt` includes `reportlab` (used for PDF export). If it is missing, run `pip install reportlab` and add the line `reportlab` to the file.

Keep `requirements.txt` in the repository. If a dependency is missing at runtime, check the import in `main.py` or `tools.py`, add the corresponding package to `requirements.txt`, and reinstall the requirements.

### 4. Install Ollama and download the model

Install Ollama from the official download page:

https://ollama.com/download

Then download the model used by the application:

```powershell
ollama pull qwen2.5:3b
```

Confirm that it is available:

```powershell
ollama list
```

The model name in Ollama must match the model configured in `main.py`. Ensure the Ollama service is running before starting the Flask application.

### 5. Check the project files

Confirm that these files and folders are present:

- `main.py`
- `tools.py`
- `pdf_export.py`
- `index.html` (in the project root)
- `requirements.txt`

The current backend serves `index.html` from the project root. Keep the root-level `index.html` alongside `main.py`. The `templates/` folder is present in your local directory, but do not move the root-level HTML file into it unless you also change the Flask route.

### 6. (Optional) Use a second LLM for Version B

By default both versions use `qwen2.5:3b`. To compare two different models, pull another one and set `MODEL_B` before starting the app:

```powershell
ollama pull llama3.2:3b
$env:MODEL_B = "llama3.2:3b"
python main.py
```

Version A always runs the tool-using agent, so `MODEL_A` (default `qwen2.5:3b`) must support tool calling. Version B is plain text generation, so any chat model works.

### 7. Run the application

From the project root, with the virtual environment activated and Ollama running, execute:

```powershell
python main.py
```

Wait for Flask to report that the development server is running. Then open the local address shown in the terminal. If the application uses Flask's default local port, open:

http://127.0.0.1:5000

Keep the terminal open while using the application. The terminal displays backend and agent activity and may show errors from the model or research tools.

## How to Use Research AI

1. Open the application in your browser.
2. Enter a clear research topic in the research input.
3. Submit the topic and wait while the agent gathers information and writes both versions (this takes longer than a single version).
4. Read the results. Use the tabs to switch between **Version A: Detailed Paper** and **Version B: Executive Brief**.
5. Review the source URLs and tools shown by the application. Open and verify sources before relying on them.
6. Click **Download PDF** (next to the tabs) or **Save Report (PDF)** (bottom of the page) to download the version you are viewing as a PDF.
7. Submit another topic when you want to begin a new research run.

Generation time depends on your hardware, model, topic complexity, and external research tools. PDFs are also stored locally in the `reports/` folder; they are not uploaded to GitHub.

## Backend Routes

The backend routes currently expected by the frontend are:

| Route           | Method | Purpose                                                                                       |
| --------------- | ------ | --------------------------------------------------------------------------------------------- |
| `/`             | GET    | Serves the web interface.                                                                     |
| `/api/health`   | GET    | Checks whether the backend is responding.                                                     |
| `/research`     | POST   | Accepts a research topic and returns both versions (`research.versions`).                     |
| `/download-pdf` | POST   | Receives the chosen version and returns it as a PDF download (a copy is saved in `reports/`). |

If routes are changed in `main.py`, update this table to match the implementation.

## Troubleshooting

### The website does not open

- Confirm that `python main.py` is still running.
- Open the local address printed in the terminal.
- Start the application from the project root so Flask can find the root-level `index.html`.
- Review the terminal for Python or Flask errors.

### Ollama or the model is unavailable

Run:

```powershell
ollama list
```

Confirm that `qwen2.5:3b` is listed and that Ollama is running. If necessary, download the model again:

```powershell
ollama pull qwen2.5:3b
```

### Python reports `ModuleNotFoundError`

Activate the virtual environment and reinstall dependencies:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Research tools fail

The search and Wikipedia integrations may depend on internet access and external services. Check the terminal output and review the tool definitions in `tools.py`.

### Research generation is slow

Local inference performance depends on available memory, CPU/GPU resources, and model size. External search requests can also add delay. Try a more focused query and check the terminal for errors.

### PDF download fails

- Run `pip install reportlab` inside the virtual environment.
- Check the Flask terminal for the error message.
- Saved copies are in the `reports/` folder next to `main.py`; the folder is excluded from Git.

## Privacy and Repository Hygiene

Before publishing the repository:

- Ensure `.gitignore` excludes `venv/`, `__pycache__/`, `.env`, and `reports/`.
- Do not commit API keys, passwords, personal data, or private configuration.
- Review `backupmain.py` before publishing it; it is not needed to run the main application and may contain older code.
- Keep the Python source files, root-level `index.html`, `tools.py`, `requirements.txt`, and this README in the repository.

## Limitations

- AI-generated research can contain errors, omissions, or outdated information.
- Source URLs and tool-use details should be independently checked; they do not guarantee that every claim is supported by a source.
- The application relies on the configured model and external research services.
- The Flask development server is intended for local development, not production deployment.

## Future Improvements

Potential extensions include DOCX export, stronger source verification, additional academic sources, improved error recovery, and searchable research history.

## License

No license is specified in the current project files. Add a license file and update this section if you intend to permit others to use, modify, or distribute the project.
