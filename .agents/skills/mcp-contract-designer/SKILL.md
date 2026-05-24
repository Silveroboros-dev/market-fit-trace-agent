---
name: mcp-contract-designer
description: Design MCP server contracts, including tools, resources, prompts, schemas, permissions, and safety boundaries for project-specific agent workflows.
---

# MCP Contract Designer

Design an MCP interface that is useful, narrow, and safe.

## Required Output

1. MCP purpose
2. Exposed resources
3. Exposed tools
4. Prompt templates, if any
5. Input/output schemas
6. Permission and side-effect boundaries
7. Minimal implementation plan
8. Tests and mock server strategy

## Rules

- Do not expose broad write access unless necessary.
- Prefer read-only resources first.
- Every tool must have a clear user value and a constrained schema.
- Separate retrieval/context tools from action tools.
- Include at least one example request and response.

