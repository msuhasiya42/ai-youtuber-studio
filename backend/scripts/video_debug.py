#!/usr/bin/env python3
"""
video_debug.py

Usage:
  python video_debug.py 0JeBS6MaNmw

Requires:
  - python packages: psycopg2-binary, boto3, requests, chromadb (optional)
  - environment: AWS creds in env or ~/.aws, DATABASE_URL optionally set
  - Chroma accessible at CHROMA_HOST:CHROMA_PORT (defaults to 127.0.0.1:8001)
"""

import os
import sys
import json
import psycopg2
import boto3
import requests
from urllib.parse import urlparse

# chromadb client optional
try:
    from chromadb import Client
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except Exception:
    CHROMADB_AVAILABLE = False

VIDEO_ID = sys.argv[1] if len(sys.argv) > 1 else "0JeBS6MaNmw"

# --- Postgres connection helpers ---
def get_postgres_conn():
    # Prefer DATABASE_URL if present
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return psycopg2.connect(database_url)

    # Fallback to local credentials (edit if needed)
    DB_NAME = os.getenv("PGDATABASE", "aiyoutuberstudio")
    DB_USER = os.getenv("PGUSER", "postgres")
    DB_PASS = os.getenv("PGPASSWORD", "postgres")
    DB_HOST = os.getenv("PGHOST", "localhost")
    DB_PORT = int(os.getenv("PGPORT", 5432))
    return psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)

def fetch_video_record(video_youtube_id):
    """
    Uses the correct column names:
    SELECT id, channel_id, youtube_video_id, title, thumbnail_url, duration_seconds,
           published_at, views, likes, ctr, transcript_s3_key, audio_s3_key, summary,
           processing_status, processing_error, indexed_at
      FROM public.videos
     WHERE youtube_video_id = %s
    """
    try:
        conn = get_postgres_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, channel_id, youtube_video_id, title, thumbnail_url,
                   duration_seconds, published_at, views, likes, ctr,
                   transcript_s3_key, audio_s3_key, summary, processing_status,
                   processing_error, indexed_at
            FROM public.videos
            WHERE youtube_video_id = %s
            LIMIT 1
        """, (video_youtube_id,))
        row = cur.fetchone()
        cur.close()
        conn.close()
        return row
    except Exception as e:
        print("❌ Postgres error:", e)
        return None

# --- S3 helpers ---
def s3_client():
    # boto3 will pick creds from env or config; override region if set
    region = os.getenv("AWS_REGION", None)
    if region:
        return boto3.client("s3", region_name=region)
    return boto3.client("s3")

def list_s3_objects_for_video(bucket, video_id):
    out = {}
    s3 = s3_client()
    for prefix in ("audio/", "transcripts/"):
        try:
            resp = s3.list_objects_v2(Bucket=bucket, Prefix=f"{prefix}{video_id}")
            keys = [o["Key"] for o in resp.get("Contents", [])]
            out[prefix] = keys
        except Exception as e:
            out[prefix] = f"Error: {e}"
    return out

# --- Chroma helpers (try python client, fallback to REST) ---
def try_chroma_client_default():
    """Try default (local) python client: Client(Settings())"""
    if not CHROMADB_AVAILABLE:
        return False, "chromadb python package not installed"
    try:
        client = Client(Settings())  # default settings
        # list_collections returns a list-like object; safe to print names
        cols = client.list_collections()
        return True, cols
    except Exception as e:
        return False, f"default client failed: {repr(e)}"

def try_chroma_client_rest(host, port):
    """Try python client configured to use the REST server"""
    if not CHROMADB_AVAILABLE:
        return False, "chromadb python package not installed"
    try:
        client = Client(Settings(
            chroma_api_impl="rest",
            chroma_server_host=host,
            chroma_server_http_port=int(port),
        ))
        cols = client.list_collections()
        return True, cols
    except Exception as e:
        return False, f"rest-python-client failed: {repr(e)}"

def probe_chroma_rest_endpoints(host, port):
    """
    Probe a list of common REST endpoints to find one that returns collections.
    Returns (True, info) on success or (False, error_summary).
    """
    base = f"http://{host}:{port}"
    endpoints = [
        "/api/v2/collections",
        "/api/v1/collections",
        "/collections",
        "/api/collections",
        "/api/v2/collection/list",
        "/api/v1/collection/list",
    ]
    session = requests.Session()
    session.headers.update({"User-Agent": "video_debug/1.0"})
    good = []
    errors = {}
    for ep in endpoints:
        url = base + ep
        try:
            resp = session.get(url, timeout=6)
            if resp.ok:
                # attempt parse JSON safely
                try:
                    j = resp.json()
                except Exception:
                    j = resp.text[:2000]
                good.append((ep, j))
            else:
                errors[ep] = f"status {resp.status_code}: {resp.text[:400]}"
        except Exception as e:
            errors[ep] = repr(e)
    if good:
        return True, good  # list of working endpoints + payload
    return False, errors

def check_chroma(host="127.0.0.1", port=8001):
    # Allow overriding via env
    host = os.getenv("CHROMA_HOST", host)
    port = int(os.getenv("CHROMA_PORT", port))
    print(f"\n→ Checking Chroma at {host}:{port}")

    # 1) Try default python client (best for local)
    ok, payload = try_chroma_client_default()
    if ok:
        print("\n🧠 Chroma python client (default) connected.")
        cols = payload
        try:
            # print collection names without assuming structure
            print("Collections (python client):")
            if not cols:
                print("  (none)")
            else:
                for c in cols:
                    try:
                        name = c.name if hasattr(c, "name") else c.get("name", str(c))
                    except Exception:
                        name = str(c)
                    print("  -", name)
        except Exception:
            print("  (could not enumerate collections cleanly)")
        return True

    # If default python client failed, attempt to use python client in REST mode
    print("\n⚠ Default python client failed:", payload)
    print("→ Trying python client in REST mode (chroma_api_impl='rest') ...")
    ok2, payload2 = try_chroma_client_rest(host, port)
    if ok2:
        print("\n🧠 Chroma python client (REST) connected.")
        cols = payload2
        try:
            print("Collections (python-rest client):")
            if not cols:
                print("  (none)")
            else:
                for c in cols:
                    try:
                        name = c.name if hasattr(c, "name") else c.get("name", str(c))
                    except Exception:
                        name = str(c)
                    print("  -", name)
        except Exception:
            print("  (could not enumerate collections cleanly)")
        return True

    print("\n⚠ Python REST client failed:", payload2)
    print("→ Probing common REST endpoints directly with HTTP ...")
    ok3, probe = probe_chroma_rest_endpoints(host, port)
    if ok3:
        print("\n🧠 Found working REST endpoint(s):")
        for ep, body in probe:
            print(f"  {ep} -> payload (trimmed):")
            if isinstance(body, (dict, list)):
                s = json.dumps(body, indent=2)
                print(s[:3000])
            else:
                print(str(body)[:2000])
        return True
    else:
        print("\n❌ No working REST endpoints found. Errors:")
        # print a small summary of errors
        for ep, err in probe.items():
            print(f"  {ep}: {err}")
        return False

# --- Main script flow ---
def main(video_id):
    print(f"\n🔎 Debugging video id = {video_id}\n")

    # 1) Postgres
    pg_row = fetch_video_record(video_id)
    if pg_row:
        (vid_id, channel_id, youtube_video_id, title, thumbnail_url,
         duration_seconds, published_at, views, likes, ctr,
         transcript_s3_key, audio_s3_key, summary, processing_status,
         processing_error, indexed_at) = pg_row

        print("🎬 Postgres Record Found:")
        print(f"  id: {vid_id}")
        print(f"  channel_id: {channel_id}")
        print(f"  youtube_video_id: {youtube_video_id}")
        print(f"  title: {title}")
        print(f"  thumbnail_url: {thumbnail_url}")
        print(f"  duration_seconds: {duration_seconds}")
        print(f"  published_at: {published_at}")
        print(f"  views: {views}")
        print(f"  likes: {likes}")
        print(f"  ctr: {ctr}")
        print(f"  transcript_s3_key: {transcript_s3_key}")
        print(f"  audio_s3_key: {audio_s3_key}")
        print(f"  summary: {summary}")
        print(f"  processing_status: {processing_status}")
        print(f"  processing_error: {processing_error}")
        print(f"  indexed_at: {indexed_at}")
    else:
        print("❌ No Postgres record found or Postgres error (see message above).")

    # 2) S3 check
    bucket = os.getenv("AWS_S3_BUCKET", "ai-youtube-data")
    print(f"\n→ Checking S3 bucket: {bucket}")
    s3_info = list_s3_objects_for_video(bucket, video_id)
    for prefix, result in s3_info.items():
        print(f"  {prefix}: {result}")

    # 3) Chroma
    chroma_ok = check_chroma()
    if not chroma_ok:
        print("\n⚠ Chroma checks failed. See messages above.")
    else:
        print("\n✅ Chroma checks succeeded.")

if __name__ == "__main__":
    main(VIDEO_ID)