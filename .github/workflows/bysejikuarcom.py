import base64
import json
import os
import sys
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# ── Default Hardcoded Input URL (Used if no argument/env provided) ─────────────
DEFAULT_PAGE_URL = "https://bysejikuar.com/e/c3dvgxc1jdrt"
# ─────────────────────────────────────────────────────────────────────────────

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"


def b64url_decode(s: str) -> bytes:
    s = s.replace("-", "+").replace("_", "/")
    pad = len(s) % 4
    if pad != 0:
        s += "=" * (4 - pad)
    return base64.b64decode(s)


def get_key_indices(version: str, length: int) -> list[int]:
    try:
        n = int(version.strip())
        if 1 <= n <= 20:
            a = n
            b = 31 - n
            if 1 <= a <= length and 1 <= b <= length:
                return [a, b]
    except Exception:
        pass
    return []


def decrypt_playback(playback: dict) -> dict:
    version = playback.get("version", "")
    key_parts = playback.get("key_parts", [])
    iv_b64 = playback.get("iv", "")
    payload_b64 = playback.get("payload", "")

    indices = get_key_indices(version, len(key_parts))
    if indices:
        selected_parts = [key_parts[i - 1] for i in indices]
    else:
        selected_parts = key_parts

    key_bytes = b"".join(b64url_decode(p) for p in selected_parts)
    iv_bytes = b64url_decode(iv_b64)
    payload_bytes = b64url_decode(payload_b64)

    aesgcm = AESGCM(key_bytes)
    decrypted = aesgcm.decrypt(iv_bytes, payload_bytes, None)
    return json.loads(decrypted.decode("utf-8"))


def extract_bysejikuar(url: str) -> dict:
    url = url.strip()
    code = url.rstrip("/").split("/")[-1]
    api_url = f"https://bysejikuar.com/api/videos/{code}"

    resp = requests.get(
        api_url,
        headers={
            "User-Agent": UA,
            "Referer": url,
            "Origin": "https://bysejikuar.com",
            "Accept": "application/json, text/plain, */*",
        },
        timeout=20,
    )
    resp.raise_for_status()

    data = resp.json()
    playback = data.get("playback", {})
    sources_data = decrypt_playback(playback)

    sources = sources_data.get("sources", [])
    master_m3u8 = sources[0]["url"] if sources else None

    return {
        "status": "success",
        "input_url": url,
        "title": data.get("title"),
        "code": code,
        "duration_seconds": data.get("duration_seconds"),
        "poster_url": data.get("poster_url"),
        "master_m3u8": master_m3u8,
        "sources": sources,
    }


def write_github_summary(results: list[dict]):
    summary_file = os.getenv("GITHUB_STEP_SUMMARY")
    if not summary_file:
        return

    try:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write("## 🎬 Bysejikuar Stream Extraction Results\n\n")
            for res in results:
                if res.get("status") == "success":
                    f.write(f"### {res.get('title', 'Unknown Title')}\n")
                    f.write(f"- **Video Code:** `{res.get('code')}`\n")
                    f.write(f"- **Duration:** {res.get('duration_seconds')}s\n")
                    f.write(f"- **Master M3U8:** [{res.get('master_m3u8')}]({res.get('master_m3u8')})\n\n")
                    f.write("| Quality | Mime Type | Stream URL |\n")
                    f.write("|---|---|---|\n")
                    for s in res.get("sources", []):
                        f.write(f"| {s.get('label', 'Source')} | `{s.get('mime_type')}` | [Direct Stream]({s.get('url')}) |\n")
                    f.write("\n---\n")
                else:
                    f.write(f"### ❌ Extraction Failed for `{res.get('input_url')}`\n")
                    f.write(f"- **Error:** {res.get('error')}\n\n")
    except Exception as e:
        print(f"Warning: Failed to write to GITHUB_STEP_SUMMARY: {e}", file=sys.stderr)


def main():
    # 1. Determine input URLs from CLI args, Environment Variable, or default Hardcoded URL
    input_str = ""
    if len(sys.argv) > 1:
        input_str = " ".join(sys.argv[1:])
    elif os.getenv("PAGE_URL"):
        input_str = os.getenv("PAGE_URL")
    elif os.getenv("TARGET_URL"):
        input_str = os.getenv("TARGET_URL")
    else:
        input_str = DEFAULT_PAGE_URL

    # Support multiple comma/space/newline separated URLs if provided
    raw_urls = [u.strip() for u in input_str.replace(",", " ").replace("\n", " ").split(" ") if u.strip()]
    if not raw_urls:
        raw_urls = [DEFAULT_PAGE_URL]

    all_results = []

    for url in raw_urls:
        print("=" * 60)
        print(f"Processing URL: {url}")
        try:
            res = extract_bysejikuar(url)
            all_results.append(res)
            print(f"Title       : {res['title']}")
            print(f"Code        : {res['code']}")
            print(f"Duration    : {res['duration_seconds']}s")
            print(f"Poster      : {res['poster_url']}")
            print(f"Master M3U8 : {res['master_m3u8']}")
            print("\nAll Available Sources:")
            for s in res["sources"]:
                print(f"  [{s.get('label', 'Source')}] ({s.get('mime_type')}) -> {s.get('url')}")
        except Exception as err:
            print(f"Error extracting {url}: {err}")
            all_results.append({
                "status": "error",
                "input_url": url,
                "error": str(err)
            })
        print("=" * 60 + "\n")

    # Output JSON file
    output_filename = "bysejikuar_extracted.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"Saved results to {output_filename}")

    # Write GitHub Actions Step Summary if running in CI
    write_github_summary(all_results)


if __name__ == "__main__":
    main()
