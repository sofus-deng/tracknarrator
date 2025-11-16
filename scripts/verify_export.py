#!/usr/bin/env python3
import sys
import json
import hmac
import hashlib
import zipfile
import os

SECRET = os.getenv("TN_SHARE_SECRET") or os.getenv("SHARE_SECRET") or "tn-export"

def main(p):
    with zipfile.ZipFile(p, "r") as z:
        man = json.loads(z.read("MANIFEST.json").decode())
        sig = z.read("SIGNATURE.txt").decode().strip()
        mbytes = json.dumps(man, separators=(",", ":"), sort_keys=True).encode()
        want = hmac.new(SECRET.encode(), mbytes, hashlib.sha256).hexdigest()
        if sig != want:
            print("BAD: signature mismatch")
            sys.exit(2)
        for f in man["files"]:
            if f["name"] in ("MANIFEST.json","SIGNATURE.txt"):
                continue
            sha = hashlib.sha256(z.read(f["name"])).hexdigest()
            if sha != f["sha256"]:
                print("BAD: hash mismatch for", f["name"])
                sys.exit(3)
        print("OK")

if __name__=="__main__":
    main(sys.argv[1])