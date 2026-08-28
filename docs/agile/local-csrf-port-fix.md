# Local Docker CSRF origin handling

Finopser's Docker deployment supports changing the frontend host port with `APP_PORT`. Django's CORS and CSRF trusted origins must follow that port or session-authenticated POST requests fail origin validation.

The Compose configuration derives both settings from `APP_PORT` and trusts the two loopback hostnames used for local testing:

- `http://localhost:${APP_PORT}`
- `http://127.0.0.1:${APP_PORT}`

This keeps local port changes working without requiring users to manually duplicate the port into separate Django settings. Production deployments should continue to set explicit HTTPS origins appropriate to the deployed hostname.