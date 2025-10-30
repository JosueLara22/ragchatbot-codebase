# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync --extra dev
   ```

   Note: Use `--extra dev` to install development dependencies including code formatters

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Development

### Code Quality Tools

This project uses Black for automatic code formatting to maintain consistent style throughout the codebase.

#### Format Code

To format all Python files:

**On Linux/Mac:**
```bash
./format.sh
```

**On Windows:**
```bash
format.bat
```

**Or directly with uv:**
```bash
uv run black .
```

#### Check Formatting

To check if code is properly formatted without making changes:

**On Linux/Mac:**
```bash
./check-format.sh
```

**On Windows:**
```bash
check-format.bat
```

**Or directly with uv:**
```bash
uv run black --check --diff .
```

#### Run All Quality Checks

To run all code quality checks:

**On Linux/Mac:**
```bash
./quality-check.sh
```

**On Windows:**
```bash
quality-check.bat
```

### Black Configuration

Black is configured in `pyproject.toml` with the following settings:
- Line length: 88 characters
- Target Python version: 3.13
- Excludes common directories like `.venv`, `build`, `dist`, etc.

