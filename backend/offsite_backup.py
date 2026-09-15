"""Optional S3-compatible backup upload with download/restore verification."""
import argparse
import json
import os
import time
import uuid
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlparse
from backup_health import file_digest
from database_backup import inspect_database, copy_database


def make_client():
    import boto3
    from botocore.config import Config
    endpoint=os.getenv("BACKUP_S3_ENDPOINT") or None
    if endpoint and (urlparse(endpoint).scheme!="https" or not urlparse(endpoint).hostname):
        raise ValueError("Offsite endpoint must use HTTPS")
    return boto3.client("s3",endpoint_url=endpoint,region_name=os.getenv("AWS_DEFAULT_REGION","us-east-1"),
        config=Config(connect_timeout=5,read_timeout=30,retries={"mode":"standard","total_max_attempts":3}))


def publish_backup(source: Path, directory: Path, client=None):
    bucket=os.getenv("BACKUP_S3_BUCKET","").strip()
    if not bucket:return None
    prefix=os.getenv("BACKUP_S3_PREFIX","reeltogether/backups").strip('/')
    if not prefix or '..' in prefix.split('/'):
        raise ValueError("Invalid offsite prefix")
    client=client or make_client()
    key=f"{prefix}/{source.stem}-{uuid.uuid4().hex}.sqlite"
    digest=file_digest(source)
    extra={"ContentType":"application/octet-stream","Metadata":{"sha256":digest}}
    encryption=os.getenv("BACKUP_S3_ENCRYPTION","AES256")
    if encryption not in {"AES256","aws:kms","bucket-default"}:raise ValueError("Unsupported backup encryption setting")
    if encryption!="bucket-default":extra["ServerSideEncryption"]=encryption
    if encryption=="aws:kms":
        kms=os.getenv("BACKUP_S3_KMS_KEY_ID","")
        if not kms:raise ValueError("A key identifier is required for managed-key encryption")
        extra["SSEKMSKeyId"]=kms
    # Upload only a verified local snapshot, never the database currently in use.
    original=inspect_database(source)
    client.upload_file(str(source),bucket,key,ExtraArgs=extra)
    with TemporaryDirectory(prefix="offsite-restore-",dir=directory) as temporary:
        downloaded=Path(temporary)/"downloaded.sqlite"
        client.download_file(bucket,key,str(downloaded))
        downloaded.chmod(0o600)
        if file_digest(downloaded)!=digest or inspect_database(downloaded)!=original:
            raise ValueError("Downloaded offsite backup failed verification")
    status={"ok":True,"verified_at":time.time(),"bucket":bucket,"key":key,"sha256":digest}
    pending=directory/"offsite-status.tmp"
    pending.write_text(json.dumps(status));pending.chmod(0o600);pending.replace(directory/"offsite-status.json")
    return status


def restore_offsite(key: str, expected_digest: str, destination: Path, client=None):
    bucket=os.getenv("BACKUP_S3_BUCKET","").strip()
    if not bucket:raise ValueError("Configure an offsite bucket first")
    if destination.exists():raise ValueError("Restore destination already exists")
    if len(expected_digest)!=64 or any(c not in '0123456789abcdef' for c in expected_digest):raise ValueError("A verified SHA-256 digest is required")
    client=client or make_client()
    with TemporaryDirectory(prefix="offsite-download-") as temporary:
        source=Path(temporary)/"download.sqlite"
        client.download_file(bucket,key,str(source));source.chmod(0o600)
        if file_digest(source)!=expected_digest:raise ValueError("Offsite digest does not match")
        return copy_database(source,destination)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('key');parser.add_argument('sha256');parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    try:
        restore_offsite(args.key,args.sha256,args.destination)
        print(json.dumps({"restored":True,"scope":"Restored to a new file; the running database was not replaced."}))
    except Exception as error:
        raise SystemExit("Offsite restore failed: "+type(error).__name__) from None
