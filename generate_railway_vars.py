"""
ReviewGuard — Railway Env Var Generator.
Generates base64-encoded versions of your credential files
for pasting into Railway's environment variables.
"""
import base64
from pathlib import Path

files = {
    "GOOGLE_CREDENTIALS_B64": "service_account.json",
    "GMAIL_TOKEN_B64": "token.json",
}

print("=" * 50)
print("  Railway Environment Variable Generator")
print("=" * 50)
print()

for env_var, filename in files.items():
    path = Path(filename)
    if path.exists():
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        print(f"--- {env_var} ---")
        print(encoded)
        print()
    else:
        print(f"⚠️  {filename} not found, skipping {env_var}")
        print()

print("=" * 50)
print("Copy each value above and paste it into Railway's")
print("Variables tab for your service.")
print("=" * 50)
