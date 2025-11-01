#!/usr/bin/env python3

"""
Connection Test Script for AI YouTuber Studio
Tests connectivity to all required services
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

import psycopg2
import redis
import boto3
from botocore.exceptions import ClientError
import requests
from openai import OpenAI
import google.generativeai as genai


# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    NC = '\033[0m'  # No Color


def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}{text}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")


def test_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.NC}")


def test_failure(message, error=None):
    print(f"{Colors.RED}✗ {message}{Colors.NC}")
    if error:
        print(f"  Error: {error}")


def test_warning(message):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.NC}")


def test_postgresql():
    """Test PostgreSQL RDS connection"""
    print_header("Testing PostgreSQL (AWS RDS)")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        test_failure("DATABASE_URL not set in .env")
        return False

    try:
        # Parse connection string
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()

        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        test_success(f"Connected to PostgreSQL")
        print(f"  Database: {database_url.split('@')[1].split('/')[0]}")
        print(f"  Version: {version.split(',')[0]}")
        return True

    except Exception as e:
        test_failure("PostgreSQL connection failed", str(e))
        return False


def test_redis():
    """Test Redis connection (via SSH tunnel)"""
    print_header("Testing Redis (via SSH Tunnel)")

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        test_failure("REDIS_URL not set in .env")
        return False

    try:
        r = redis.from_url(redis_url)

        # Test ping
        response = r.ping()
        if not response:
            test_failure("Redis ping failed")
            return False

        # Test set/get
        r.set("test_key", "test_value", ex=5)
        value = r.get("test_key")

        if value == b"test_value":
            test_success("Connected to Redis")
            print(f"  URL: {redis_url}")
            print(f"  Status: Operational")
            return True
        else:
            test_failure("Redis read/write test failed")
            return False

    except Exception as e:
        test_failure("Redis connection failed", str(e))
        test_warning("Make sure SSH tunnel is running: ./scripts/start_tunnels.sh")
        return False


def test_chromadb():
    """Test ChromaDB connection (via SSH tunnel)"""
    print_header("Testing ChromaDB (via SSH Tunnel)")

    chroma_host = os.getenv("CHROMA_HOST", "127.0.0.1")
    chroma_port = os.getenv("CHROMA_PORT", "8001")

    try:
        url = f"http://{chroma_host}:{chroma_port}/api/v2/heartbeat"
        response = requests.get(url, timeout=5)

        if response.status_code == 200:
            data = response.json()
            test_success("Connected to ChromaDB")
            print(f"  Host: {chroma_host}:{chroma_port}")
            print(f"  Heartbeat: {data}")
            return True
        else:
            test_failure(f"ChromaDB returned status {response.status_code}")
            return False

    except Exception as e:
        test_failure("ChromaDB connection failed", str(e))
        test_warning("Make sure SSH tunnel is running: ./scripts/start_tunnels.sh")
        test_warning("Make sure ChromaDB is running on EC2: docker-compose up -d chroma")
        return False


def test_s3():
    """Test AWS S3 connection"""
    print_header("Testing AWS S3")

    bucket_name = os.getenv("AWS_S3_BUCKET")
    aws_region = os.getenv("AWS_REGION", "us-east-1")
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

    if not bucket_name:
        test_failure("AWS_S3_BUCKET not set in .env")
        return False

    if not access_key or access_key == "YOUR_AWS_ACCESS_KEY_HERE":
        test_failure("AWS_ACCESS_KEY_ID not set or using placeholder")
        test_warning("Get your AWS credentials from AWS IAM Console")
        return False

    if not secret_key or secret_key == "YOUR_AWS_SECRET_ACCESS_KEY_HERE":
        test_failure("AWS_SECRET_ACCESS_KEY not set or using placeholder")
        test_warning("Get your AWS credentials from AWS IAM Console")
        return False

    try:
        s3 = boto3.client(
            's3',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=aws_region
        )

        # Test bucket access
        s3.head_bucket(Bucket=bucket_name)

        # List objects (limit 1 to test permissions)
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=1)

        test_success("Connected to AWS S3")
        print(f"  Bucket: {bucket_name}")
        print(f"  Region: {aws_region}")
        print(f"  Permissions: OK")

        if 'Contents' in response:
            print(f"  Objects: {response['KeyCount']} (showing sample)")

        return True

    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == '404':
            test_failure(f"S3 bucket '{bucket_name}' not found")
        elif error_code == '403':
            test_failure(f"Access denied to S3 bucket '{bucket_name}'")
            test_warning("Check your IAM permissions")
        else:
            test_failure(f"S3 error: {error_code}", str(e))
        return False

    except Exception as e:
        test_failure("S3 connection failed", str(e))
        return False


def test_openai():
    """Test OpenAI API connection"""
    print_header("Testing OpenAI API")

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key or api_key == "YOUR_OPENAI_API_KEY_HERE":
        test_failure("OPENAI_API_KEY not set or using placeholder")
        test_warning("Get your API key from https://platform.openai.com/api-keys")
        return False

    try:
        client = OpenAI(api_key=api_key)

        # Test with a simple API call
        models = client.models.list()

        test_success("Connected to OpenAI API")
        print(f"  API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"  Models available: {len(models.data)}")
        return True

    except Exception as e:
        test_failure("OpenAI API connection failed", str(e))
        test_warning("Check your API key and billing status")
        return False


def test_gemini():
    """Test Google Gemini API connection"""
    print_header("Testing Google Gemini API")

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        test_failure("GEMINI_API_KEY not set in .env")
        return False

    try:
        genai.configure(api_key=api_key)

        # List available models
        models = list(genai.list_models())

        test_success("Connected to Google Gemini API")
        print(f"  API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"  Models available: {len(models)}")

        # Show some available models
        gemini_models = [m.name for m in models if 'gemini' in m.name.lower()][:3]
        if gemini_models:
            print(f"  Gemini models: {', '.join(gemini_models)}")

        return True

    except Exception as e:
        test_failure("Gemini API connection failed", str(e))
        test_warning("Check your API key")
        return False


def main():
    """Run all connection tests"""
    print(f"\n{Colors.MAGENTA}")
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║                                                           ║")
    print("║        AI YouTuber Studio - Connection Tests             ║")
    print("║                                                           ║")
    print("╚═══════════════════════════════════════════════════════════╝")
    print(f"{Colors.NC}\n")

    # Run all tests
    results = {
        "PostgreSQL (RDS)": test_postgresql(),
        "Redis": test_redis(),
        "ChromaDB": test_chromadb(),
        "AWS S3": test_s3(),
        # "OpenAI API": test_openai(),
        "Gemini API": test_gemini(),
    }

    # Summary
    print_header("Test Summary")

    total = len(results)
    passed = sum(results.values())
    failed = total - passed

    for service, status in results.items():
        status_text = f"{Colors.GREEN}PASS{Colors.NC}" if status else f"{Colors.RED}FAIL{Colors.NC}"
        print(f"  {service:.<40} {status_text}")

    print(f"\n{Colors.BLUE}{'─'*60}{Colors.NC}")
    print(f"  Total: {total} | Passed: {Colors.GREEN}{passed}{Colors.NC} | Failed: {Colors.RED}{failed}{Colors.NC}")
    print(f"{Colors.BLUE}{'─'*60}{Colors.NC}\n")

    if passed == total:
        print(f"{Colors.GREEN}✓ All services are connected and operational!{Colors.NC}\n")
        print("You're ready to start the application:")
        print("  ./scripts/start_all.sh")
        print("")
        return 0
    else:
        print(f"{Colors.YELLOW}⚠ Some services failed connection tests{Colors.NC}\n")
        print("Please fix the failed services before starting the application.")
        print("")
        return 1


if __name__ == "__main__":
    sys.exit(main())
