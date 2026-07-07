"""Immutable raw-match archival: always local disk, optionally S3/MinIO.

If `S3_ENDPOINT_URL` is unset the archiver writes only to `data/raw/`. When it
is set (e.g. http://localhost:9000 for MinIO), each raw match is also uploaded
to the configured bucket under `henrik/<match_id>.json`.
"""
import json
import os
import sys

# Make the shared `config` module importable regardless of working directory
# (temporary shim until the backend is packaged with __init__.py files).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import config

_s3_client = None
_s3_ready = False


def _get_s3():
    """Lazily build the S3/MinIO client and ensure the bucket exists.

    Returns None when S3 is not configured, so callers fall back to local-only.
    """
    global _s3_client, _s3_ready
    if not config.S3_ENDPOINT_URL:
        return None
    if _s3_ready:
        return _s3_client
    try:
        import boto3
        _s3_client = boto3.client(
            "s3",
            endpoint_url=config.S3_ENDPOINT_URL,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            region_name=config.S3_REGION,
        )
        # Ensure the bucket exists (idempotent).
        buckets = {b["Name"] for b in _s3_client.list_buckets().get("Buckets", [])}
        if config.S3_BUCKET not in buckets:
            _s3_client.create_bucket(Bucket=config.S3_BUCKET)
    except Exception as e:  # noqa: BLE001 — degrade gracefully to local-only
        print(f"  ! S3/MinIO unavailable ({e}); archiving locally only.")
        _s3_client = None
    _s3_ready = True
    return _s3_client


def local_dir() -> str:
    return os.path.join(str(config.REPO_ROOT), "data", "raw")


def archive_match(match_id: str, raw: dict) -> None:
    """Persist one raw match to local disk and (if configured) S3/MinIO."""
    payload = json.dumps(raw, ensure_ascii=False).encode("utf-8")

    # 1) Local disk (immutable archive alongside the DB).
    d = local_dir()
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"{match_id}_henrik.json"), "wb") as f:
        f.write(payload)

    # 2) Optional S3/MinIO.
    s3 = _get_s3()
    if s3 is not None:
        s3.put_object(
            Bucket=config.S3_BUCKET,
            Key=f"henrik/{match_id}.json",
            Body=payload,
            ContentType="application/json",
        )
