# Bysejikuar Stream Extractor (`bikebyse`)

Direct extractor and AES-GCM stream decryptor for `https://bysejikuar.com/e/{video_id}`.

## Features
- **AES-GCM Decryption**: Automatically calculates key indices from payload version and decrypts HLS / Master M3U8 URLs.
- **GitHub Actions Ready**: Run with single click via `workflow_dispatch` with hardcoded default.
- **CLI & Local Ready**: Run locally with custom URLs or use default.

## Installation
```bash
pip install -r requirements.txt
```

## Local Usage
```bash
# Run with default hardcoded URL
python bysejikuarcom.py

# Run with custom URL
python bysejikuarcom.py https://bysejikuar.com/e/c3dvgxc1jdrt
```
