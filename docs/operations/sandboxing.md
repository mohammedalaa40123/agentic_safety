# Sandbox Isolation

## Code execution isolation

Code execution is handled by tools/code_exec.py and supports:

- auto: prefers bwrap when present.
- bwrap: requires bubblewrap namespace isolation.
- none: local execution path.

## Recommended secure settings

```yaml
sandbox:
  enabled: true
  tools: [file_io, code_exec, web_browse]
  code_exec_backend: bwrap
  code_exec_require_isolation: true
  code_timeout: 10
  max_steps: 5
```

## Runtime protections

- CPU limit via RLIMIT_CPU.
- Memory limit via RLIMIT_AS.
- Output file size limit via RLIMIT_FSIZE.
- Network unshared when bwrap backend is active.

## Fail-closed mode

If no isolation backend is available and code_exec_require_isolation is true, code execution is blocked rather than falling back to local execution.
