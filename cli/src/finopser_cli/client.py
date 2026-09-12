import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class FinopserClientError(RuntimeError):
    pass


@dataclass(frozen=True)
class FinopserClient:
    base_url: str
    token: str
    timeout: float = 15.0

    def __post_init__(self):
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Finopser URL must be an absolute http:// or https:// URL.")
        if not self.token.strip():
            raise ValueError("A Finopser API token is required.")

    def get(self, path: str):
        url = urljoin(self.base_url.rstrip("/") + "/", path.lstrip("/"))
        request = Request(
            url,
            method="GET",
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.token}",
                "User-Agent": "finopser-cli/0.1",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                payload = response.read().decode("utf-8")
        except HTTPError as exc:
            detail = self._http_error_detail(exc)
            raise FinopserClientError(f"Finopser returned HTTP {exc.code}: {detail}") from None
        except URLError as exc:
            raise FinopserClientError(f"Unable to reach Finopser: {exc.reason}") from None

        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            raise FinopserClientError("Finopser returned a non-JSON response.") from None

    @staticmethod
    def _http_error_detail(exc: HTTPError) -> str:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return "request failed"
        detail = payload.get("detail") if isinstance(payload, dict) else None
        return str(detail) if detail else "request failed"
