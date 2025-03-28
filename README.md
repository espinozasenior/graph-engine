# graph-engine

Graph-Engine is an open-source module for **automatically building and maintaining dependency graphs** of your codebase, with a particular focus on scalability, modularity, and test-driven development. This project is licensed under the **Hippocratic License**, aligning with ethical standards in software creation.

## Vision and Roadmap

The long-term goal of Graph-Engine is to support a **multi-language** environment, collect both **static** (AST-based) and **dynamic** (runtime instrumentation) data, and store it in a **graph database** for large-scale analysis and integration into **autonomous/self-evolving** AI systems. Our development will follow these main phases:

1. **Phase 1 (MVP)**:  
   - Single-language (Python) static analysis using an **in-memory graph**.  
   - Real-time file watching for code changes.  
   - A minimal REST API exposing graph data.  
   - **Complete test coverage** for every function and file, ensuring expected inputs/outputs are verified.

2. **Phase 2**:  
   - Multi-language support (e.g., JavaScript, Java).  
   - Dynamic instrumentation to capture real runtime calls.  
   - Graph database integration (JanusGraph).

3. **Phase 3**:  
   - Visualization with Cytoscape.js front-end.  
   - Incremental parsing improvements, rename detection, secrets masking.

4. **Phase 4**:  
   - CI/CD integration, performance tuning, artifact generation.

5. **Phase 5**:  
   - AI agent plugin architecture for code refactoring, code generation, and extended community-driven enhancements.

**Note**: We aim to produce well-structured, modular Python code with a strong emphasis on **test-driven development** (TDD). Each function, class, or module will have corresponding tests, specifying the **expected inputs and outputs**. This approach ensures reliability and maintainability as the project grows.

## License

This project is published under the [Hippocratic License](https://firstdonoharm.dev/). Please review the license terms to understand the ethical guidelines and usage limitations.

## Contributing

Contributions are welcomed! Please submit pull requests or open issues with questions and feedback. For larger changes or new language parsers, please open an issue first to discuss the approach.

## Getting Started

1. **Clone or Fork** this repository.
2. **Install dependencies** from `requirements.txt`.
3. **Run Tests**: `pytest --maxfail=1 --disable-warnings -q`
4. **Start the Watcher/API** (coming soon in Phase 1).

Stay tuned for more updates!