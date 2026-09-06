"""Source retrieval with an official-host allowlist and hard safety limits.

Downloaded content is ALWAYS treated as untrusted (spec section 71):
  * strict host allowlist - redirects off the allowlist are refused
  * hard byte cap (defends against zip/entity bombs and oversized files)
  * no execution, no archive extraction, no XML entity resolution here
    (parsers use defused settings)
"""

from __future__ import annotations

import json
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

MAX_BYTES = 60 * 1024 * 1024        # 60 MB per artifact
CONNECT_TIMEOUT = 30
USER_AGENT = "AegisAI-Governance-RegulatoryIngest/0.2 (+compliance content sync; contact: admin)"

# Only official publishers. A redirect to anything not on this list aborts the fetch.
ALLOWED_HOSTS = {
    "eur-lex.europa.eu", "publications.europa.eu", "data.europa.eu",
    "nvlpubs.nist.gov", "csrc.nist.gov", "www.nist.gov", "nist.gov", "airc.nist.gov",
    "raw.githubusercontent.com", "github.com", "api.github.com", "objects.githubusercontent.com",
    "codeload.github.com", "release-assets.githubusercontent.com", "github-releases.githubusercontent.com",
    "raw.githack.com",
    "atlas.mitre.org",
    "www.gov.uk", "assets.publishing.service.gov.uk",
    "www.meity.gov.in", "meity.gov.in", "www.indiacode.nic.in", "egazette.gov.in",
    "aiverifyfoundation.sg", "www.imda.gov.sg", "genai.owasp.org", "owasp.org",
}


class DisallowedHost(RuntimeError):
    pass


class SourceTooLarge(RuntimeError):
    pass


@dataclass
class FetchResult:
    content: bytes
    retrieved_url: str
    http_status: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    mime_type: Optional[str] = None
    file_name: Optional[str] = None
    mode: str = "single"


def _check_host(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if host not in ALLOWED_HOSTS:
        raise DisallowedHost(f"host {host!r} is not on the official-source allowlist ({url})")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_host(newurl)  # allow redirects, but only to official hosts
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(_NoRedirect())


def fetch_single(url: str, *, accept: Optional[str] = None, retries: int = 3) -> FetchResult:
    _check_host(url)
    headers = {"User-Agent": USER_AGENT}
    if accept:
        headers["Accept"] = accept
    last_err: Optional[Exception] = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with _opener().open(req, timeout=CONNECT_TIMEOUT) as resp:
                raw = resp.read(MAX_BYTES + 1)
                if len(raw) > MAX_BYTES:
                    raise SourceTooLarge(f"{url} exceeds {MAX_BYTES} bytes")
                ctype = resp.headers.get("Content-Type", "")
                return FetchResult(
                    content=raw,
                    retrieved_url=resp.geturl(),
                    http_status=resp.status,
                    headers={k: v for k, v in resp.headers.items()
                             if k.lower() in {"content-type", "content-length", "last-modified", "etag", "date"}},
                    mime_type=ctype.split(";")[0].strip() or None,
                    file_name=url.rstrip("/").split("/")[-1] or None,
                )
        except (urllib.error.URLError, socket.timeout, TimeoutError) as e:  # noqa: PERF203
            last_err = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"failed to retrieve {url} after {retries} attempts: {last_err}")


def fetch_bundle(files: List[Dict[str, str]]) -> FetchResult:
    """Retrieve several files and assemble a deterministic JSON bundle."""
    out: Dict[str, str] = {}
    for entry in files:
        res = fetch_single(entry["url"])
        out[entry["name"]] = res.content.decode("utf-8", errors="replace")
    payload = json.dumps({"files": out}, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return FetchResult(content=payload, retrieved_url=files[0]["url"] if files else "",
                       mime_type="application/json", file_name="bundle.json", mode="bundle")


# -- NIST CPRT recursive graph retrieval ------------------------------------
_CPRT_BASE = "https://csrc.nist.gov/extensions/nudp/services/json/nudp/framework/version"


def _cprt_graph(version_id: str, element: Optional[str] = None) -> List[Dict[str, Any]]:
    url = f"{_CPRT_BASE}/{version_id}/graph" if not element else f"{_CPRT_BASE}/{version_id}/element/{element}/graph"
    res = fetch_single(url, accept="application/json")
    doc = json.loads(res.content.decode("utf-8"))
    return doc.get("response", {}).get("elements", []) or []


def fetch_cprt(version_id: str, deep_from_type: str) -> FetchResult:
    """BFS the CPRT graph. ``deep_from_type`` is the element type whose per-element
    graph call already returns the full subtree (e.g. 'category' for CSF,
    'practice' for SSDF), so we stop drilling there."""
    roots = _cprt_graph(version_id)
    resolved: List[Dict[str, Any]] = []

    def resolve(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        acc = []
        for el in elements:
            etype = el.get("elementTypeIdentifier")
            if etype == deep_from_type:
                deep = _cprt_graph(version_id, el["elementIdentifier"])
                # deep response re-includes ancestors; find this element in it
                node = _find(deep, el["elementIdentifier"]) or el
                acc.append(node)
            elif el.get("elements"):
                el = dict(el)
                el["elements"] = resolve(el["elements"])
                acc.append(el)
            else:
                # one level down
                child = _cprt_graph(version_id, el["elementIdentifier"])
                node = _find(child, el["elementIdentifier"])
                if node and node.get("elements"):
                    el = dict(el)
                    el["elements"] = resolve(node["elements"])
                acc.append(el)
        return acc

    resolved = resolve(roots)
    payload = json.dumps(
        {"framework_version_identifier": version_id, "tree": resolved},
        sort_keys=True, ensure_ascii=False,
    ).encode("utf-8")
    return FetchResult(content=payload, retrieved_url=f"{_CPRT_BASE}/{version_id}/graph",
                       mime_type="application/json", file_name=f"{version_id}.cprt.json", mode="cprt")


def fetch_github_release_asset(repo: str, asset_glob: str) -> FetchResult:
    """Resolve the latest published release of ``repo`` and download the first
    asset whose name matches ``asset_glob`` (fnmatch). Records nothing here - the
    pipeline stores repo + resolved tag + sha256."""
    import fnmatch

    api = f"https://api.github.com/repos/{repo}/releases/latest"
    meta = json.loads(fetch_single(api, accept="application/vnd.github+json").content.decode("utf-8"))
    tag = meta.get("tag_name", "")
    assets = meta.get("assets", [])
    match = next((a for a in assets if fnmatch.fnmatch(a["name"], asset_glob)), None)
    if not match:
        raise RuntimeError(f"{repo} release {tag}: no asset matching {asset_glob!r} "
                           f"(have: {[a['name'] for a in assets][:10]})")
    res = fetch_single(match["browser_download_url"])
    res.mode = "github_release"
    res.headers = {**res.headers, "x-github-repo": repo, "x-github-tag": tag,
                   "x-github-asset": match["name"]}
    return res


def _resolve_ref(repo: str, ref_mode: str) -> str:
    if ref_mode == "main":
        return "main"
    if ref_mode == "latest_release":
        meta = json.loads(fetch_single(f"https://api.github.com/repos/{repo}/releases/latest",
                                       accept="application/vnd.github+json").content.decode("utf-8"))
        return meta.get("tag_name") or "main"
    if ref_mode == "latest_tag":
        tags = json.loads(fetch_single(f"https://api.github.com/repos/{repo}/tags?per_page=1",
                                       accept="application/vnd.github+json").content.decode("utf-8"))
        return tags[0]["name"] if tags else "main"
    return ref_mode  # explicit ref/sha


def fetch_github_bundle(repo: str, ref_mode: str, path_prefix: str, files: List[str]) -> FetchResult:
    ref = _resolve_ref(repo, ref_mode)
    out: Dict[str, str] = {}
    for name in files:
        url = f"https://raw.githubusercontent.com/{repo}/{ref}/{path_prefix.rstrip('/')}/{name}"
        out[name] = fetch_single(url).content.decode("utf-8", errors="replace")
    payload = json.dumps({"files": out, "repo": repo, "ref": ref, "version": ref},
                         sort_keys=True, ensure_ascii=False).encode("utf-8")
    return FetchResult(content=payload, retrieved_url=f"https://github.com/{repo}/tree/{ref}/{path_prefix}",
                       mime_type="application/json", file_name=f"{repo.replace('/', '_')}_{ref}.bundle.json",
                       mode="github_bundle", headers={"x-github-repo": repo, "x-github-ref": ref})


def _find(elements: List[Dict[str, Any]], identifier: str) -> Optional[Dict[str, Any]]:
    for el in elements:
        if el.get("elementIdentifier") == identifier:
            return el
        hit = _find(el.get("elements", []) or [], identifier)
        if hit:
            return hit
    return None
