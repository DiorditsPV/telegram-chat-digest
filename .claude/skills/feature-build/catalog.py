#!/usr/bin/env python3
"""Пересобрать каталог фич (FEATURES.md) из спек `.claude/features/*.md`. Только stdlib.

Каждая спека — источник истины по фиче. Скрипт табулирует их frontmatter
(slug, title, status, verify, review, branch, created) в корневой FEATURES.md.
Проектно-независим: запускается из любого репозитория с установленным фреймворком.

Запуск:  python3 .claude/skills/feature-build/catalog.py
Опц. env: FEATURES_DIR (по умолчанию .claude/features), FEATURES_OUT (по умолчанию FEATURES.md).
Файлы спек с именем на `_` (напр. _TEMPLATE.md) пропускаются.
"""
import os
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
FEAT_DIR = ROOT / os.environ.get("FEATURES_DIR", ".claude/features")
OUT = ROOT / os.environ.get("FEATURES_OUT", "FEATURES.md")

ORDER = {"shipped": 0, "done": 1, "building": 2, "designed": 3}


def parse_frontmatter(text: str) -> dict:
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    meta = {}
    if not m:
        return meta
    for line in m.group(1).splitlines():
        mm = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if mm:
            meta[mm.group(1).strip()] = mm.group(2).strip().strip("'\"")
    return meta


def main():
    rows = []
    if FEAT_DIR.exists():
        for f in sorted(FEAT_DIR.glob("*.md")):
            if f.name.startswith("_"):  # шаблоны/служебные файлы
                continue
            meta = parse_frontmatter(f.read_text(encoding="utf-8"))
            slug = meta.get("slug", f.stem)
            rows.append(
                {
                    "slug": slug,
                    "title": meta.get("title", slug),
                    "status": meta.get("status", "designed"),
                    "issue": meta.get("issue", "—"),
                    "verify": meta.get("verify", "—"),
                    "review": meta.get("review", "—"),
                    "branch": meta.get("branch", f"feature/{slug}"),
                    "created": meta.get("created", "—"),
                    "spec": f"{FEAT_DIR.relative_to(ROOT).as_posix()}/{f.name}",
                }
            )
    rows.sort(key=lambda r: (ORDER.get(r["status"], 9), r["slug"]))

    lines = [
        "# FEATURES.md — каталог реализованных/спроектированных фич (для ревью)",
        "",
        "Автообновляется `feature-build` (`.claude/skills/feature-build/catalog.py`, читает "
        "`.claude/features/*.md`). Каждая строка — ветка-кандидат. Посмотреть: "
        "`git switch <branch>`. Понравилось → merge в default-ветку.",
        "",
        "| ветка | slug | issue | описание | status | verify | review | дата | спека |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    if rows:
        for r in rows:
            issue = r.get("issue", "—")
            issue_cell = f"#{issue}" if issue and issue != "—" else "—"
            lines.append(
                f"| `{r['branch']}` | {r['slug']} | {issue_cell} | {r['title']} | {r['status']} | "
                f"{r['verify']} | {r['review']} | {r['created']} | {r['spec']} |"
            )
    else:
        lines.append("| _(пусто — заполнится по мере генерации фич)_ | | | | | | | | |")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"{OUT}: {len(rows)} feature(s)")


if __name__ == "__main__":
    main()
