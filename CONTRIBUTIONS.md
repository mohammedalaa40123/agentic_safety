# Contributing to Agentic Safety

We welcome contributions from the community to improve the Agentic Safety framework! 
Whether you're adding new attacks, implementing novel defenses, or expanding the benchmarking dataset, your help is appreciated.

## How to Contribute
1. **Fork the repository** and create your branch from `main`.
2. If you've added code that should be tested, **add tests**.
3. Ensure the test suite passes.
4. **Issue a pull request**!

## Areas for Contribution
- **New Attacks:** Integrating new red-teaming techniques or adversarial algorithms (e.g., pre-generated GCG suffixes, tree-of-thought jailbreaks).
- **New Defenses:** Implementing prompt-level, response-level, or tool-policy-level defenses.
- **Dataset Expansion:** Adding more CTF-like scenarios, OWASP-aligned goals, and multi-turn environments.
- **Support for More Models:** Integrating new open-source or commercial models.
- **Documentation:** Improving tutorials, architecture guides, and API documentation.

## Guidelines
- Follow standard Python styling (PEP 8).
- Ensure any added features support the existing sandboxing mechanism for safe execution.
- Maintain the modularity of the framework (attacks, defenses, and metrics should be strictly decoupled).

Thank you for helping make agentic AI systems more secure and robust!
