import json, os, re, subprocess, sys
from pathlib import Path

def check(ok):
    if not ok:
        raise ValueError("Solicitud AutoPublish invalida")

def main():
    request = Path("publication/cardputer.json")
    check(not request.is_symlink() and request.stat().st_size <= 8192)
    data = json.loads(request.read_text(encoding="utf-8"))
    check(type(data) is dict and set(data) == {"schema", "items"} and data["schema"] == 1)
    items = data["items"]
    check(isinstance(items, list) and 1 <= len(items) <= 16)
    seen = set()
    jobs = []
    for item in items:
        check(isinstance(item, dict))
        kind = item.get("kind")
        check(kind in ("launcher", "library", "app"))
        version = item.get("version")
        check(isinstance(version, str) and len(version) <= 20)
        if kind == "launcher":
            check(set(item) == {"kind", "version"} and re.fullmatch(r"0\.(8|9|10|11)[a-z]", version))
            name = "launcher"
            env = {"LAUNCHER_VERSION": version}
            script = "preparar_launcher_cardputer.py"
        else:
            check(set(item) == {"kind", "name", "version"})
            name = item["name"]
            check(isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,39}", name))
            check(re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", version))
            if kind == "library":
                check(name.startswith("m5lib_") and len(name) > 6)
            env = {"APP_NAME": name, "APP_VERSION": version}
            script = "preparar_biblioteca_cardputer.py" if kind == "library" else "preparar_cardputer.py"
        check((kind, name) not in seen)
        seen.add((kind, name))
        jobs.append((("library", "app", "launcher").index(kind), script, env))
    for _, script, env in sorted(jobs, key=lambda j:j[0]):
        print("Preparando", script, env, flush=True)
        subprocess.run([sys.executable, "-I", "tools/" + script], env=dict(os.environ, **env), check=True)
    print("Conjunto preparado y firmado", flush=True)

if __name__ == "__main__":
    main()
