from dataclasses import dataclass, field


@dataclass
class Hunk:
    old_start: int
    new_start: int
    removed_lines: list[str] = field(default_factory=list)
    added_lines: list[str] = field(default_factory=list)


@dataclass
class FileDiff:
    path: str
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def added(self) -> list[str]:
        return [line for h in self.hunks for line in h.added_lines]

    @property
    def removed(self) -> list[str]:
        return [line for h in self.hunks for line in h.removed_lines]


def parse_unified_diff(diff_text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current: FileDiff | None = None
    current_hunk: Hunk | None = None

    for raw in diff_text.splitlines():
        if raw.startswith("diff --git"):
            current = None
            current_hunk = None
        elif raw.startswith("+++ b/"):
            current = FileDiff(path=raw[6:].strip())
            files.append(current)
        elif raw.startswith("@@") and current is not None:
            parts = raw.split()
            old_start = int(parts[1].lstrip("-").split(",")[0])
            new_start = int(parts[2].lstrip("+").split(",")[0])
            current_hunk = Hunk(old_start=old_start, new_start=new_start)
            current.hunks.append(current_hunk)
        elif current_hunk is not None:
            if raw.startswith("+") and not raw.startswith("+++"):
                current_hunk.added_lines.append(raw[1:])
            elif raw.startswith("-") and not raw.startswith("---"):
                current_hunk.removed_lines.append(raw[1:])
            elif raw.startswith("\\"):
                continue

    return [f for f in files if f.path]
