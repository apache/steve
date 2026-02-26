# Coding Agent Context

This project uses `uv` for dependency management and enforces strict linting, formatting, and type-checking standards. All Coding Agents MUST follow these instructions after generating or modifying code to ensure compatibility with the project's CI/CD pipelines.

## Post-Generation Checklist

From the repository root (where this `AGENTS.md` file lives), run the following commands inside the `v3/` directory:

1.  **Code Formatting**: Format the code using `ruff`.
    ```bash
    uv run ruff format .
    ```

2.  **Linting**: Run `ruff` check to identify and fix potential issues.
    ```bash
    uv run ruff check --fix .
    ```

3.  **Type Checking**: Verify type safety with `mypy`.
    ```bash
    uv run mypy --ignore-missing-imports .
    ```

## Development Standards

- **Language**: All code, documentation, and comments MUST be written in **English**.
- **Dependencies**: Use `uv` for all dependency management tasks (e.g., `uv sync`, `uv run`).
- **CI Alignment**: These steps align with the `.github/workflows/linting.yml` and `.github/workflows/type-tests.yml` configurations.

Ensure all checks pass before considering a task complete.
