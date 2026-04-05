# Locky

Natural language to shell command. 100% local CLI powered by Gemma 4 + Ollama.

## Install

```bash
pip install -e .
```

## Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com/)

```bash
ollama pull gemma3:12b
```

## Usage

```bash
locky
```

Type in natural language, get a shell command, confirm, execute.

```
locky> Show me the files in the current directory
=> ls -la
Execute? [y/N] y
```

## License

MIT
