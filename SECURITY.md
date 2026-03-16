# Security Policy

## Supported Scope

This repository publishes templates, deployment references, runtime orchestration scripts, and documentation for `OpenClaw-Feishu-Multi-Agent`.

Security-sensitive areas include:

- any file containing deployment credentials or example account settings
- runtime orchestration scripts under `skills/openclaw-feishu-multi-agent-deploy/scripts/`
- deployment templates and example manifests
- generated artifacts accidentally committed with secrets or private infrastructure details

## Reporting a Vulnerability

If you find a security issue, please do **not** open a public GitHub issue with exploit details or live credentials.

Please report it privately to the maintainer first. Include:

- affected file or path
- impact summary
- reproduction steps
- whether secrets, tokens, or customer identifiers are exposed
- recommended mitigation if you have one

If private contact is not available, open a minimal public issue that only states:

- there is a suspected security problem
- the maintainer should contact you privately

Do not paste secrets, tokens, private keys, customer `peerId`, or production screenshots in public threads.

## Secret Handling Policy

This repository must not contain live secrets.

Examples of values that must always be redacted:

- `appSecret`
- `verificationToken`
- `encryptKey`
- API keys and bearer tokens
- private keys

Allowed publication pattern:

- real `appId` if operationally necessary
- redacted placeholders such as `<replace-aoteman-app-secret>`

Forbidden publication pattern:

- hardcoded live secrets in README, templates, example JSON, generated artifacts, or docs

## If a Secret Was Previously Exposed

Removing a secret from git content is **not** sufficient remediation.

Required follow-up actions:

1. Rotate the exposed credential at the provider immediately.
2. Revoke or disable the old credential.
3. Audit logs for suspicious use.
4. Replace any examples in this repository with placeholders.
5. Check generated artifacts and local example outputs before publishing releases.

## Safe Publishing Checklist

Before pushing public changes:

1. Search for hardcoded secrets across the repo.
2. Verify `references/generated/` does not contain live deployment material.
3. Confirm all example `appSecret` values are placeholders.
4. Re-check links to external docs and installation paths.
5. If in doubt, prefer redaction.
