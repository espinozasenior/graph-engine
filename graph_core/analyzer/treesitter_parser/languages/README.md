# Tree-sitter Language Grammars

This directory contains compiled Tree-sitter language grammars (`.so` files) that are used by the TreeSitterParser.

## Required Language Libraries

The following language libraries are required:

- `python.so`: The Tree-sitter grammar for Python
- `javascript.so`: The Tree-sitter grammar for JavaScript
- `typescript.so`: The Tree-sitter grammar for TypeScript

## Installation

To install the required language libraries, you need to:

1. Install the Tree-sitter CLI:
```bash
npm install -g tree-sitter-cli
```

2. Clone the language repositories:
```bash
git clone https://github.com/tree-sitter/tree-sitter-python
git clone https://github.com/tree-sitter/tree-sitter-javascript
git clone https://github.com/tree-sitter/tree-sitter-typescript
```

3. Build the language libraries:
```bash
cd tree-sitter-python
tree-sitter generate
tree-sitter build-wasm
cp build/python.wasm ../graph-engine/graph_core/analyzer/treesitter_parser/languages/python.so

cd ../tree-sitter-javascript
tree-sitter generate
tree-sitter build-wasm
cp build/javascript.wasm ../graph-engine/graph_core/analyzer/treesitter_parser/languages/javascript.so

cd ../tree-sitter-typescript/typescript
tree-sitter generate
tree-sitter build-wasm
cp build/typescript.wasm ../../graph-engine/graph_core/analyzer/treesitter_parser/languages/typescript.so
```

## Python Alternative

Alternatively, you can use the `tree-sitter` Python library to build the grammar files:

```python
from tree_sitter import Language

Language.build_library(
    # Store the library in the `languages` directory
    'graph_core/analyzer/treesitter_parser/languages/python.so',
    # Include one or more languages
    ['path/to/tree-sitter-python']
)

Language.build_library(
    'graph_core/analyzer/treesitter_parser/languages/javascript.so',
    ['path/to/tree-sitter-javascript']
)

Language.build_library(
    'graph_core/analyzer/treesitter_parser/languages/typescript.so',
    ['path/to/tree-sitter-typescript/typescript']
)
```

## Notes

- For production use, you should include these compiled grammar files in your project.
- The TreeSitterParser will look for these files in this directory when initializing.
- Make sure the file names match the language names expected by the parser. 