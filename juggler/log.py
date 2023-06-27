from rich.console import Console
from rich.theme import Theme

theme = Theme({
    "warning": "#f5bd22",
    "info": "#ffffff",
    "success": "#30f522",
    "error": "#f52273",
})

console = Console(theme=theme)

def info(msg):
    console.print(f"[[info]![/info]] {msg}")

def warn(msg):
    console.print(f"[[warning]W[/warning]] {msg}")

def succ(msg):
    console.print(f"[[success]+[/success]] {msg}")

def error(msg):
    console.print(f"[[error]E[/error]] {msg}")

if __name__ == "__main__":
    info("info!")
    warn("warning!")
    succ("success!")
    error("error!")