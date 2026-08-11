# Apache STeVe v3 Server Architecture

## Overview

Apache STeVe (Secure Team Voting Engine) v3 is a web-based voting system built for the Apache Software Foundation. It provides a secure, anonymous voting platform for elections, supporting multiple vote types (e.g., Yes/No/Abstain motions and Single Transferable Vote elections). The server is implemented in Python using the Quart asynchronous web framework, with a SQLite database backend for persistence.

The architecture emphasizes security, modularity, and ease of maintenance. It follows a layered design with clear separation of concerns: web handling, business logic, data access, and utilities.

## Directory Structure

```
v3/
├── server/                    # Main server application
│   ├── api.py                 # API endpoints (currently minimal)
│   ├── bin/                   # Command-line utilities
│   │   ├── load-fakedata.py   # Script to populate test data
│   │   └── tally.py           # Election tallying and reporting
│   ├── certs/                 # TLS certificates for HTTPS
│   ├── config.yaml            # Server configuration (YAML)
│   ├── docs/                  # Per-issue documentation storage
│   ├── main.py                # Application entry point
│   ├── pages.py               # Web page handlers (routes)
│   ├── static/                # Static assets (CSS, JS, images)
│   │   ├── css/
│   │   ├── js/
│   │   └── favicon.ico
│   └── templates/             # EZT templates for HTML rendering
├── steve/                     # Core business logic and data models
│   ├── crypto.py              # Cryptographic utilities (salts, keys, tokens)
│   ├── election.py            # Election model and database operations
│   ├── persondb.py            # Person/PersonDB model for voter management
│   └── vtypes/                # Vote type implementations
│       └── __init__.py        # Registry of supported vote types
└── tests/                     # (Removed in some contexts) Unit tests
```

## Key Components

### Web Layer (Quart Framework)

- **Framework**: Uses Quart, an asynchronous version of Flask, for handling HTTP requests. This allows non-blocking I/O for better performance in I/O-bound operations like database queries.
- **Routing**: Handled in `pages.py` with decorators like `@APP.get('/')`. Routes are organized by functionality (e.g., voter pages, admin pages).
- **Authentication**: Relies on external ASF authentication via `asfquart.auth`. Requires committer-level access for most operations.
- **Templates**: Uses EZT (Easy Template) for server-side rendering. Templates are stored in `templates/` and use `[variable]` syntax for substitution. Includes includes for headers/footers.
- **Static Assets**: Served from `static/` directory, including Bootstrap CSS/JS, custom CSS, and JavaScript utilities.
- **Middleware**: Includes session management, CSRF protection (placeholder), and flash messages for user feedback.

### Business Logic Layer (`steve/`)

- **Election Model** (`election.py`): Core class `Election` manages election lifecycle (creation, opening, closing). Handles issues, votes, and voter eligibility. Uses prepared SQL queries for database interactions.
- **Person Database** (`persondb.py`): Manages voter information (PID, name, email). Provides lookup and addition methods.
- **Cryptography** (`crypto.py`): Handles secure token generation, salts, and vote encryption. Uses Argon2 for key derivation.
- **Vote Types** (`vtypes/`): Modular system for different voting methods (e.g., 'yna' for Yes/No/Abstain, 'stv' for Single Transferable Vote). Registry in `__init__.py`.

### Data Layer

- **Database**: SQLite for simplicity and portability. Schema includes tables for elections, issues, votes, persons, and voter eligibility (mayvote).
- **Queries**: SQL queries are defined in a separate YAML file (referenced but not shown in provided files). Accessed via prepared statements in the `Election` class.
- **Connections**: Database connections are opened per operation or cached in the app context. Uses `sqlite3` with row factories for dict-like access.

### Utilities and Scripts (`bin/`)

- **Tallying** (`tally.py`): Command-line tool for processing election results. Uses the `Election` class to compute tallies and generate reports.
- **Data Loading** (`load-fakedata.py`): Populates the database with test data for development.

## Code Conventions

### Python Style

- **Imports**: Standard library first, then third-party (e.g., `import pathlib`, `import quart`), then local modules. Uses absolute imports within the package.
- **Constants**: All uppercase with underscores (e.g., `FMT_DATE = '%b %d'`). No abbreviations unless standard.
- **Variables**: Snake_case for locals/functions, PascalCase for classes.
- **Error Handling**: Exceptions are raised for errors (e.g., `ElectionNotFound`). No broad try/except blocks; scripts exit on failure.
- **Logging**: Uses Python's `logging` module. Root logger set to INFO to suppress third-party noise. Local loggers (e.g., `_LOGGER`) can be DEBUG. F-strings for log messages (e.g., `logger.debug(f"Processing {item}")`).
- **Async/Await**: Used throughout Quart handlers for non-blocking operations.
- **Type Hints**: Not used (per project style; avoid unless requested).
- **Docstrings**: Minimal; not enforced.

### File and Directory Layout

- **Modularity**: Each major component in its own file (e.g., `pages.py` for routes, `election.py` for model).
- **Separation**: Web logic in `server/`, business logic in `steve/`, scripts in `bin/`.
- **Configuration**: YAML for config (`config.yaml`), with defaults in code.
- **Assets**: Organized by type (CSS, JS) in `static/`.
- **Templates**: Flat structure in `templates/`, with includes for reuse.

### Database Patterns

- **Prepared Statements**: All SQL uses parameterized queries to prevent injection.
- **Transactions**: Implicit in SQLite; explicit commits for multi-step operations.
- **Schema Evolution**: Not shown; assumes schema is static or handled externally.
- **Joins and Counts**: Queries use JOINs for related data (e.g., voter counts via `mayvote` table).

### Security

- **Authentication**: External (ASF OAuth); no local auth.
- **Authorization**: Role-based (committer, PMC member) via decorators.
- **Encryption**: Votes are encrypted; keys derived securely.
- **CSRF**: Placeholder token in forms; not fully implemented.
- **HTTPS**: Enforced via TLS certificates in `certs/`.

### Development and Deployment

- **Entry Point**: `main.py` with `if __name__ == '__main__'` for standalone, ASGI for production.
- **Configuration**: Loaded from `config.yaml` relative to app directory.
- **Testing**: Unit tests in `tests/` (removed in some contexts).
- **Dependencies**: Managed via `uv` (Python package manager); includes Quart, asfpy, etc.

## Patterns and Idioms

- **Decorator-Based Loading**: `@load_election` and `@load_election_issue` decorators fetch and pass database objects to handlers.
- **EasyDict Usage**: `edict` from `easydict` for dict-like objects with attribute access (e.g., `result.election = election.get_metadata()`).
- **Template Rendering**: `asfquart.utils.render()` for EZT templates.
- **Flash Messages**: Session-based user feedback using Quart's flash system.
- **Stopwatch**: `asfpy.stopwatch.Stopwatch()` for performance monitoring in debug mode.
- **EZT Boolean Flags**: `ezt.boolean()` for conditional rendering in templates.
- **Randomization**: Shuffles candidate lists to avoid bias in STV elections.

This architecture supports scalable, secure voting while remaining maintainable and extensible.
