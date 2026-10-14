# Research AI

Research AI is a locally run, AI-assisted research paper generation application. It combines a browser-based interface with a Flask backend, a locally hosted language model through Ollama, and research tools for gathering and synthesizing information.

Users submit a research topic through the web interface. The research agent can use the configured search and Wikipedia tools, then generates a structured research-paper-style response. The interface displays the result and available source/tool information, and users can save completed research to a local text file.

## Features

- Accepts natural-language research topics.
- Generates structured, research-paper-style responses.
- Runs the language model locally through Ollama using `qwen2.5:3b`.
- Uses LangChain to coordinate the model and configured research tools.
- Integrates web-search and Wikipedia tools defined in `tools.py`.
- Provides a browser-based interface for submitting topics and reading results.
- Displays source URLs and tools reported for the research run.
- Allows completed research to be saved to `research_output.txt`.
- Includes a backend health check and terminal logging.

## Technology Stack

| Component | Technology |
|---|---|
| Frontend | HTML, CSS, JavaScript |
| Backend | Python, Flask |
| Language-model runtime | Ollama |
| Language model | Qwen2.5:3B |
| Agent orchestration | LangChain |
| Research tools | Search and Wikipedia integrations configured in `tools.py` |

## Project Structure

The current project directory is organized as follows:

```text
ai-agent/
├── main.py                 # Main Flask application and research agent
├── backupmain.py           # Backup copy of the backend; not used to start the app
├── tools.py                # Research tool definitions
├── index.html              # Web interface served by Flask
├── templates/               # Existing folder; retain if used by your code
├── requirements.txt        # Python dependencies
├── .env                    # Local environment configuration, if needed
├── .gitignore              # Files excluded from Git
├── research_output.txt     # Locally saved research; generated/updated by the app
├── venv/                   # Local Python virtual environment; do not commit
└── README.md               # Project documentation
```

The `venv/`, `__pycache__/`, `.env`, and `research_output.txt` entries are local/runtime files and should not be uploaded to a public repository. `backupmain.py` is retained as a backup; run `main.py` for the application.

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
- `index.html` (in the project root)
- `requirements.txt`

The current backend serves `index.html` from the project root. Keep the root-level `index.html` alongside `main.py`. The `templates/` folder is present in your local directory, but do not move the root-level HTML file into it unless you also change the Flask route.

### 6. Run the application

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
3. Submit the topic and wait while the agent gathers information and generates the response.
4. Read the generated research paper in the results area.
5. Review the source URLs and tools shown by the application. Open and verify sources before relying on them.
6. Use **Save Research** to save the completed result to `research_output.txt`, if that feature is available in the current interface.
7. Submit another topic when you want to begin a new research run.

Generation time depends on your hardware, model, topic complexity, and external research tools. Saved research is stored locally; it is not automatically uploaded to GitHub.

## Backend Routes

The backend routes currently expected by the frontend are:

| Route | Method | Purpose |
|---|---|---|
| `/` | GET | Serves the web interface. |
| `/api/health` | GET | Checks whether the backend is responding. |
| `/research` | POST | Accepts a research topic and returns the generated result. |
| `/save` | POST | Saves a completed research result to a local text file. |

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

### Saved research is missing

Check whether `research_output.txt` exists in the project directory. The file is local to the machine running the Flask backend. It is excluded from Git so that personal or generated research is not accidentally published.

## Privacy and Repository Hygiene

Before publishing the repository:

- Ensure `.gitignore` excludes `venv/`, `__pycache__/`, `.env`, and `research_output.txt`.
- Do not commit API keys, passwords, personal data, or private configuration.
- Review `backupmain.py` before publishing it; it is not needed to run the main application and may contain older code.
- Keep the Python source files, root-level `index.html`, `tools.py`, `requirements.txt`, and this README in the repository.

## Limitations

- AI-generated research can contain errors, omissions, or outdated information.
- Source URLs and tool-use details should be independently checked; they do not guarantee that every claim is supported by a source.
- The application relies on the configured model and external research services.
- The Flask development server is intended for local development, not production deployment.

## Future Improvements

Potential extensions include PDF/DOCX export, stronger source verification, additional academic sources, improved error recovery, and searchable research history.

## License

No license is specified in the current project files. Add a license file and update this section if you intend to permit others to use, modify, or distribute the project.
