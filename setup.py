import subprocess
# "anthropic>=0.51.0", 
packages = ["arxiv>=2.2.0", "mcp>=1.7.1", "pypdf2>=3.0.1", 
            "python-dotenv>=1.1.0", "typing>=3.10.0.0", "uv", "openai"]

for package in packages:
    try:
        print(f"Installing {package}...")
        subprocess.check_call(["pip", "install"] + package.split())
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")