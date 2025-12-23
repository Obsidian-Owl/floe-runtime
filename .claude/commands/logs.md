# Log Analysis Command (Context-Efficient)

Analyse Docker or Kubernetes logs without consuming context window.

## Usage

```
/project:logs [container-or-pod] [optional: error-focus]
```

## Examples

```
/project:logs polaris
/project:logs dagster-webserver connection
/project:logs localstack "access denied"
```

## What This Command Does

1. **Spawns docker-log-analyser agent** (not main context)
2. **Extracts only error lines** (--tail + grep)
3. **Returns structured diagnosis** (not raw logs)

## Implementation

When invoked, delegate to the docker-log-analyser agent:

```
Task(docker-log-analyser, "
Analyse logs for: $1
Error focus: $2 (or general errors)

Protocol:
1. Check container/pod status first
2. Extract last 30 lines with error filtering
3. Return: Root cause, Fix, Verification command

CRITICAL: Do NOT paste full logs. Summarise findings.
")
```

## Why This Matters

**Without delegation**: 100+ lines of logs in context = context exhaustion
**With delegation**: 5-line diagnosis = context preserved

## Integration with k8s-debug

For complex K8s debugging (helm charts, multiple pods):
- Use `/project:k8s-debug` instead
- It coordinates both agents
