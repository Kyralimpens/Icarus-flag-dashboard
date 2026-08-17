#!/usr/bin/env python3
"""Generate a password hash for the USERS env var. Run locally; never commit real passwords.
Usage:  python3 gen_password.py kyra
It prompts for the password (hidden) and prints a JSON snippet to paste into USERS."""
import sys, os, hashlib, getpass, json


def hash_password(pw, iterations=240000):
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


if __name__ == "__main__":
    username = sys.argv[1] if len(sys.argv) > 1 else input("username: ").strip()
    pw = getpass.getpass("password: ")
    pw2 = getpass.getpass("confirm : ")
    if pw != pw2:
        sys.exit("passwords do not match")
    if len(pw) < 8:
        sys.exit("use at least 8 characters")
    print("\nAdd this user to the USERS env var (JSON). Example for one user:\n")
    print("USERS=" + json.dumps({username: hash_password(pw)}))
    print("\nFor multiple users, merge them into one JSON object:")
    print('USERS={"kyra":"pbkdf2_sha256$...","cass":"pbkdf2_sha256$..."}')
