# Worker operations

## Preflight

From the backend directory, run:

```bash
python -m app.worker_preflight
```

This is a read-only diagnostic. It checks Python, common command-line tools, optional
ML package presence, free disk space and whether `nvidia-smi` can report a GPU.
It does not install software, download weights or prove inference works.

## Security rules

- Run workers under a dedicated operating-system account.
- Keep worker credentials in environment variables or a secret manager.
- Never place worker secrets in browser JavaScript, project JSON or Git.
- Do not expose a GPU worker directly to the public internet.
- Restrict writable paths to dedicated temporary and output directories.
- Apply process, memory, disk and wall-clock limits to every generation.
- Treat prompts, uploaded images and model outputs as untrusted input.
- Delete temporary files according to an explicit retention policy.

## Local development

The Docker Compose stack is loopback-bound and suitable only for local development.
A public deployment needs authentication, rate limits, private object storage, TLS,
request quotas, audit logging, worker isolation and a durable scheduler.
