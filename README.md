# SayAThing

[![Build Status](https://img.shields.io/github/actions/workflow/status/kanthorlabs/sayathing/ci.yml?branch=main)](https://github.com/kanthorlabs/sayathing/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version](https://img.shields.io/badge/version-25.9.1-green.svg)](https://github.com/kanthorlabs/sayathing/releases)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

> **Open Source Platform That Gives Your Text a Voice**

SayAThing is a production-ready text-to-speech (TTS) service that converts text into natural-sounding speech using advanced AI models. Built with FastAPI and powered by the Kokoro TTS engine, it provides a robust API for developers to integrate high-quality speech synthesis into their applications.

## ✨ Features

- **🎯 RESTful API**: Clean, well-documented API endpoints for text-to-speech conversion
- **🔄 Async Processing**: Background task queue system for handling multiple requests efficiently
- **🎭 Multiple Voices**: Support for various voice profiles and languages via Kokoro engine
- **📊 Web Dashboard**: Real-time monitoring interface for tasks and system status
- **🐳 Docker Ready**: Containerized deployment with production-grade configuration
- **🔧 Dependency Injection**: Clean architecture with proper separation of concerns
- **📈 Scalable**: Multi-worker support for handling concurrent requests
- **🛡️ Robust**: Built-in retry mechanisms and error handling

## 🚀 Quick Start

### Prerequisites

- Python 3.12 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation

#### Option 1: Using uv (Recommended)

```bash
# Clone the repository
git clone https://github.com/kanthorlabs/sayathing.git
cd sayathing

# Install dependencies
uv sync

# Run the service
uv run python main.py
```

#### Option 2: Using pip

```bash
# Clone the repository
git clone https://github.com/kanthorlabs/sayathing.git
cd sayathing

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Run the service
python main.py
```

#### Option 3: Using Docker

```bash
# Clone and build
git clone https://github.com/kanthorlabs/sayathing.git
cd sayathing

# Build and run with Docker
docker build -t sayathing .
docker run -p 8000:8000 sayathing
```

### Basic Usage

Once the service is running, you can:

1. **Access the API**: `http://localhost:8000`
2. **View API docs**: `http://localhost:8000/docs`
3. **Monitor dashboard**: `http://localhost:8000/ui/dashboard`

#### Convert Text to Speech

```bash
curl -X POST "http://localhost:8000/api/tts" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world! This is SayAThing speaking.",
    "voice_id": "kokoro.af_heart"
  }'
```

#### Get Available Voices

```bash
curl "http://localhost:8000/api/voices"
```

## 🏗️ Architecture

SayAThing follows a clean architecture pattern with these key components:

- **HTTP Server**: FastAPI-based REST API
- **Worker Queue**: SQLite-backed task processing system
- **TTS Engine**: Kokoro-powered speech synthesis
- **Database**: SQLAlchemy ORM with async SQLite
- **Dependency Injection**: Container-based service management

## 🧑‍💻 Development

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make test-coverage

# Run integration tests
make test-integration

# Run all checks (linting + tests)
make check
```

### Available Commands

```bash
# Development server with auto-reload
uv run python main-dev.py

# Run specific worker configurations
uv run python main.py --primary-workers 2 --retry-workers 1

# Run without HTTP server (workers only)
uv run python main.py --no-http

# View all available options
uv run python main.py --help
```

### Project Structure

```
sayathing/
├── server/          # FastAPI application and routes
├── tts/             # Text-to-speech engine interfaces
├── worker/          # Background task processing
├── data/            # SQLite database storage
├── docs/            # Documentation
└── main.py          # Application entry point
```

## 📖 API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tts` | POST | Convert text to speech |
| `/api/voices` | GET | List available voices |
| `/api/tasks/{task_id}` | GET | Get task status |
| `/ui/dashboard` | GET | Web monitoring dashboard |
| `/health` | GET | Health check endpoint |

For detailed API documentation, visit `/docs` when the service is running.

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Install development dependencies: `uv sync --group dev`
4. Make your changes and add tests
5. Run the test suite: `make test-all`
6. Commit your changes: `git commit -m 'Add amazing feature'`
7. Push to the branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Code Standards

- Follow [PEP 8](https://pep8.org/) style guidelines
- Add type hints for all functions
- Write tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Kokoro TTS](https://github.com/kokoro-ai/kokoro) - The excellent TTS engine powering speech synthesis
- [FastAPI](https://fastapi.tiangolo.com/) - The modern, fast web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - The Python SQL toolkit

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/kanthorlabs/sayathing/issues)
- **Discussions**: [GitHub Discussions](https://github.com/kanthorlabs/sayathing/discussions)

---

**Made with ❤️ by [KanthorLabs](https://github.com/kanthorlabs)**
