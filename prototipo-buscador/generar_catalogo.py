#!/usr/bin/env python3
"""Generate a JSON search catalog from CoBAM TEI XML files.

Run from any directory with Python 3:
    python prototipo-buscador/generar_catalogo.py

The source XML files are read-only; the output is written only to
prototipo-buscador/catalogo.json.
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

TEI_NS = "http://www.tei-c.org/ns/1.0"
NS = {"tei": TEI_NS}
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent
OUTPUT = HERE / "catalogo.json"


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def text_of(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return clean(" ".join(element.itertext()))


def first_text(root: ET.Element, path: str) -> str:
    return text_of(root.find(path, NS))


def first_nonempty(*values: str) -> str:
    return next((v for v in values if v), "")


def get_years(date_el: ET.Element | None, title: str, filename: str) -> tuple[int | None, int | None]:
    candidates: list[str] = []
    if date_el is not None:
        for attr in ("from", "notBefore", "when", "to", "notAfter", "until"):
            value = date_el.get(attr)
            if value:
                candidates.append(value)
    # Prefer explicit date attributes; otherwise use human-readable date/title,
    # then the date convention used in CoBAM filenames.
    explicit = [int(m.group(1)) for value in candidates for m in [re.search(r"\\b(15\\d{2}|16\\d{2})\\b", value)] if m]
    if explicit:
        start = explicit[0]
        end = explicit[1] if len(explicit) > 1 else start
        return min(start, end), max(start, end)

    for source in (text_of(date_el), title, filename):
        years = [int(y) for y in re.findall(r"\\b(?:15|16)\\d{2}\\b", source)]
        if years:
            return min(years), max(years)
    return None, None


def action_info(root: ET.Element, action_type: str) -> tuple[str, str]:
    action = root.find(f".//tei:correspAction[@type='{action_type}']", NS)
    if action is None:
        return "", ""
    person = text_of(action.find("tei:persName", NS))
    place = first_nonempty(
        text_of(action.find("tei:settlement", NS)),
        text_of(action.find("tei:placeName", NS)),
        text_of(action.find("tei:region", NS)),
        text_of(action.find("tei:country", NS)),
    )
    return person, place


def make_record(path: Path, root: ET.Element) -> dict:
    title = first_nonempty(
        first_text(root, ".//tei:fileDesc/tei:titleStmt/tei:title[@level='a']"),
        first_text(root, ".//tei:fileDesc/tei:titleStmt/tei:title"),
        path.stem,
    )
    sent = root.find(".//tei:correspAction[@type='sent']", NS)
    date_el = sent.find("tei:date", NS) if sent is not None else root.find(".//tei:correspAction/tei:date", NS)
    date_label = text_of(date_el)
    sender, origin = action_info(root, "sent")
    recipient, destination = action_info(root, "received")
    abstract = first_text(root, ".//tei:note[@type='abstract']")
    incipit = first_text(root, ".//tei:note[@type='incipit']")
    language = first_text(root, ".//tei:langUsage/tei:language")
    xml_id = root.get("{http://www.w3.org/XML/1998/namespace}id", "")
    idno = first_text(root, ".//tei:publicationStmt/tei:idno[@type='CoBAM']")
    body = root.find(".//tei:text[@type='source']/tei:body", NS)
    if body is None:
        body = root.find(".//tei:text/tei:body", NS)
    full_text = text_of(body)
    start_year, end_year = get_years(date_el, title, path.name)
    url = "https://github.com/CoBAM-editor/CoBAM/blob/main/" + quote(path.name, safe="")
    return {
        "id": xml_id or path.stem,
        "title": title,
        "date": date_label or idno or path.stem,
        "start_year": start_year,
        "end_year": end_year,
        "sender": sender,
        "recipient": recipient,
        "origin": origin,
        "destination": destination,
        "language": language,
        "abstract": abstract,
        "incipit": incipit,
        "text": full_text,
        "file": path.name,
        "url": url,
    }


def main() -> int:
    records: list[dict] = []
    errors: list[str] = []
    for path in sorted(REPO_ROOT.glob("*.xml"), key=lambda p: p.name.casefold()):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        # Only index TEI correspondence entries, not schema/configuration XML.
        if root.tag != f"{{{TEI_NS}}}TEI":
            continue
        if root.find(".//tei:correspDesc", NS) is None:
            continue
        records.append(make_record(path, root))

    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Catálogo generado: {OUTPUT.relative_to(REPO_ROOT)} ({len(records)} cartas)")
    if errors:
        print(f"Aviso: {len(errors)} archivo(s) no se pudieron leer:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
    if not records:
        print("No se encontraron XML-TEI con correspDesc. Revisa la estructura del repositorio.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
