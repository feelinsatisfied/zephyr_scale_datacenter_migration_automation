# Certificates Directory

This directory contains TLS/SSL certificates for secure connections to your Jira instances.

## Optional Files

If your environment requires certificate-based authentication or custom CA certificates:

| File | Description |
|------|-------------|
| `ca_cert.crt` | CA certificate for TLS verification |
| `client_cert.crt` | Client certificate for mutual TLS |
| `client_key.key` | Client private key for mutual TLS |

## When to Use

- **Standard HTTPS**: No certificates needed if using public CAs
- **Self-signed certificates**: Add your CA certificate
- **Mutual TLS / Client certificates**: Add both client cert and key

## Security Note

Certificate files are excluded from version control via `.gitignore`.

**Never commit private keys or certificates to a public repository.**
