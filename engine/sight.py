"""
Optics & Local Machine Sight for Hew.
Provides safe, depth-controlled file inspection of the workspace.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Noise to hide so Hew doesn't drown in system files
IGNORED = {".git", "__pycache__", ".venv", "node_modules", ".vscode", ".obsidian"}


def get_file_tree(folder: str = "", max_depth: int = 2) -> str:
    """
    Returns an ASCII tree structure of a directory (like Windows 'tree /F /A'),
    safely capped by depth to prevent context overload.
    
    Args:
        folder: Relative folder from project root (e.g. '', 'journal', 'mirror'). Default is root.
        max_depth: Maximum folder levels deep to explore. Default is 2.
    """
    try:
        start_dir = (PROJECT_ROOT / folder.strip("/\\")).resolve()
        if not start_dir.exists() or not start_dir.is_dir():
            return f"[Notice] Directory '{folder}' does not exist."

        lines = [f"📂 {start_dir.name or 'Asimilex'}/"]

        def walk(current_dir: Path, current_depth: int, prefix: str = ""):
            if current_depth > max_depth:
                return

            items = [
                item for item in sorted(current_dir.iterdir())
                if item.name not in IGNORED and not item.name.startswith(".")
            ]

            for i, item in enumerate(items):
                is_last = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                sub_prefix = "    " if is_last else "│   "

                if item.is_dir():
                    lines.append(f"{prefix}{connector}📁 {item.name}/")
                    walk(item, current_depth + 1, prefix + sub_prefix)
                else:
                    lines.append(f"{prefix}{connector}📄 {item.name}")

        walk(start_dir, 1)
        return "\n".join(lines)
    except Exception as e:
        return f"[Error] Could not generate file tree: {e}"


def read_text(file_path: str, max_chars: int = 4000) -> str:
    """
    Reads markdown, notes, articles, or text files from the machine.
    
    Args:
        file_path: Relative path to the file (e.g. 'journal/2026-10-28.md', 'notes.md').
        max_chars: Maximum characters to read. Default is 4000.
    """
    try:
        target = (PROJECT_ROOT / file_path.strip("/\\")).resolve()
        
        # Fallback search in journal/ if user only gave filename
        if not target.exists():
            alt = PROJECT_ROOT / "journal" / file_path.strip("/\\")
            if alt.exists():
                target = alt
            else:
                return f"[Error] File '{file_path}' not found."

        if target.is_dir():
            return f"[Error] '{file_path}' is a folder. Use get_file_tree instead."

        text = target.read_text(encoding="utf-8", errors="replace")
        total = len(text)
        preview = text[:max_chars]
        
        truncation = f"\n\n[... Truncated: showing {max_chars} of {total} chars]" if total > max_chars else ""
        return f"=== {target.name} ({total} chars) ===\n{preview}{truncation}"
    except Exception as e:
        return f"[Error] Could not read file: {e}"


SIGHT_TOOLS = [
    get_file_tree,
    read_text,
]