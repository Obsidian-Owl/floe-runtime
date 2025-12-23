# Kubernetes Debug Command

Debug a Kubernetes deployment or pod with context-efficient log extraction.

## Usage

```
/project:k8s-debug [namespace] [pod-or-deployment-name]
```

## Workflow

1. **Delegate to helm-debugger agent** for chart/deployment issues
2. **Delegate to docker-log-analyser agent** for container runtime issues
3. Return structured diagnosis without dumping full logs

## Important

This command spawns subagents to preserve main context. Do NOT paste full logs into the main conversation.

## Example

```
/project:k8s-debug default dagster-webserver-abc123
```

Will:
1. Check pod status
2. Extract only error lines from logs
3. Return root cause and fix
