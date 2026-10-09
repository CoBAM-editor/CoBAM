#!/usr/bin/env python3
"""Build a faceted search catalogue from CoBAM TEI-XML correspondence files."""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

TEI_NS = "http://www.tei-c.org/ns/1.0"
XML_NS = "http://www.w3.org/XML/1998/namespace"
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


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        value = clean(value)
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            result.append(value)
    return result


def get_years(date_el: ET.Element | None, title: str, filename: str) -> tuple[int | None, int | None]:
    candidates: list[str] = []
    if date_el is not None:
        # Gather all available date attributes before deriving the interval:
        # TEI often stores start/end in separate from/to values.
        for attr in ("from", "notBefore", "when", "to", "notAfter", "until"):
            value = date_el.get(attr)
            if value:
                candidates.append(value)
    explicit = [
        int(year)
        for value in candidates
        for year in re.findall(r"\b(?:15|16)\d{2}\b", value)
    ]
    if explicit:
        return min(explicit), max(explicit)
    for source in (text_of(date_el), title, filename):
        years = [int(y) for y in re.findall(r"\b(?:15|16)\d{2}\b", source)]
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


def body_text(text_el: ET.Element | None) -> str:
    if text_el is None:
        return ""
    body = text_el.find("tei:body", NS)
    return text_of(body if body is not None else text_el)


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
    language_elements = root.findall(".//tei:langUsage/tei:language", NS)
    languages = unique([text_of(el) for el in language_elements])
    language_codes = unique([el.get("ident", "") for el in language_elements if el.get("ident")])
    language = languages[0] if languages else ""
    language_code = language_codes[0] if language_codes else ""
    date_when = date_el.get("when", "") if date_el is not None else ""
    date_from = first_nonempty(
        date_el.get("from", "") if date_el is not None else "",
        date_el.get("notBefore", "") if date_el is not None else "",
        date_when,
    )
    date_to = first_nonempty(
        date_el.get("to", "") if date_el is not None else "",
        date_el.get("notAfter", "") if date_el is not None else "",
        date_when,
    )
    date_certainty = first_nonempty(
        date_el.get("cert", "") if date_el is not None else "",
        date_el.get("precision", "") if date_el is not None else "",
    )
    xml_id = root.get(f"{{{XML_NS}}}id", "")
    letter_code = first_text(root, ".//tei:publicationStmt/tei:idno[@type='CoBAM']")
    start_year, end_year = get_years(date_el, title, path.name)

    source_el = root.find(".//tei:text[@type='source']", NS)
    if source_el is None:
        source_el = root.find(".//tei:text[tei:body]", NS)
    transcription = body_text(source_el)
    translation_el = root.find(".//tei:text[@type='translation']", NS)
    translation = body_text(translation_el)
    # Notes embedded in the edited text are treated as annotation/searchable notes,
    # kept separate from the header abstract and incipit.
    notes_in_text = unique([text_of(n) for n in root.findall(".//tei:text//tei:note", NS)])
    apparatus_entries = unique([text_of(a) for a in root.findall(".//tei:text//tei:app", NS)])
    critical_apparatus = " ".join(apparatus_entries)
    annotations = " ".join(notes_in_text + apparatus_entries)

    def entity_values(paths: list[str]) -> list[str]:
        return unique([text_of(el) for xpath in paths for el in root.findall(xpath, NS)])

    sender_places = [origin] if origin else []
    recipient_places = [destination] if destination else []
    all_places = unique(sender_places + recipient_places + entity_values([
        ".//tei:text//tei:placeName",
        ".//tei:text//tei:name[@type='place']",
        ".//tei:text//tei:rs[@type='place']",
        ".//tei:text//tei:name[@type='county']",
    ]))
    named_people = entity_values([
        ".//tei:text//tei:name[@type='person']",
        ".//tei:text//tei:persName",
        ".//tei:text//tei:rs[@type='person']",
    ])
    organizations = entity_values([
        ".//tei:text//tei:orgName",
        ".//tei:text//tei:name[@type='organization']",
        ".//tei:text//tei:rs[@type='organization']",
    ])
    mentioned_entities: list[dict[str, str]] = []
    seen_entities: set[tuple[str, str, str, str]] = set()
    entity_specs = [
        (".//tei:text//tei:name", "name"),
        (".//tei:text//tei:rs", "rs"),
        (".//tei:text//tei:persName", "person"),
        (".//tei:text//tei:placeName", "place"),
        (".//tei:text//tei:orgName", "organization"),
    ]
    for xpath, element_kind in entity_specs:
        for entity_el in root.findall(xpath, NS):
            label = text_of(entity_el)
            if not label:
                continue
            kind = entity_el.get("type", "")
            if not kind:
                kind = element_kind
            ref = entity_el.get("ref", "")
            key = entity_el.get("key", "")
            signature = (kind, label, ref, key)
            if signature in seen_entities:
                continue
            seen_entities.add(signature)
            mentioned_entities.append({"type": kind, "label": label, "ref": ref, "key": key})

    repositories: list[str] = []
    archive_countries: list[str] = []
    archive_cities: list[str] = []
    shelfmarks: list[str] = []
    witnesses: list[dict[str, str]] = []
    for witness in root.findall(".//tei:sourceDesc/tei:listWit/tei:witness", NS):
        witness_id = witness.get(f"{{{XML_NS}}}id", "")
        ms_identifier = witness.find(".//tei:msIdentifier", NS)
        repository = text_of(ms_identifier.find("tei:msName", NS)) if ms_identifier is not None else ""
        city = text_of(ms_identifier.find("tei:settlement", NS)) if ms_identifier is not None else ""
        country = text_of(ms_identifier.find("tei:country", NS)) if ms_identifier is not None else ""
        mark = text_of(ms_identifier.find(".//tei:altIdentifier/tei:idno", NS)) if ms_identifier is not None else ""
        if repository:
            repositories.append(repository)
        if city:
            archive_cities.append(city)
        if country:
            archive_countries.append(country)
        if mark:
            shelfmarks.append(mark)
        witness_text = text_of(witness)
        if witness_text:
            witnesses.append({
                "id": witness_id,
                "repository": repository,
                "city": city,
                "country": country,
                "shelfmark": mark,
                "description": witness_text,
            })

    graphic_urls = unique([
        clean(el.get("url")) for el in root.findall(".//tei:facsimile/tei:graphic", NS)
        if el.get("url")
    ])
    bibliography = unique([
        text_of(el) for el in root.findall(".//tei:sourceDesc/tei:bibl[@type='inextenso']", NS)
    ])
    hand_notes = unique([text_of(el) for el in root.findall(".//tei:handNotes/tei:handNote", NS)])
    editor = first_text(root, ".//tei:fileDesc/tei:titleStmt/tei:editor")
    authors = unique([text_of(el) for el in root.findall(".//tei:fileDesc/tei:titleStmt/tei:author", NS)])
    revision = root.find(".//tei:revisionDesc", NS)
    edition_status = revision.get("status", "") if revision is not None else ""
    changes = root.findall(".//tei:revisionDesc/tei:change", NS)
    last_change = changes[-1] if changes else None
    revision_date = last_change.get("when", "") if last_change is not None else ""
    revision_who = last_change.get("who", "") if last_change is not None else ""

    url = "https://github.com/CoBAM-editor/CoBAM/blob/main/" + quote(path.name, safe="")
    record = {
        "id": xml_id or path.stem,
        "letter_code": letter_code.strip(" []") or xml_id or path.stem,
        "title": title,
        "date": date_label or letter_code or path.stem,
        "date_when": date_when,
        "date_from": date_from,
        "date_to": date_to,
        "date_certainty": date_certainty,
        "start_year": start_year,
        "end_year": end_year,
        "sender": sender,
        "recipient": recipient,
        "origin": origin,
        "destination": destination,
        "language": language,
        "languages": languages,
        "language_code": language_code,
        "language_codes": language_codes,
        "abstract": abstract,
        "incipit": incipit,
        "transcription": transcription,
        "translation": translation,
        "annotations": annotations,
        "critical_apparatus": critical_apparatus,
        "text": " ".join(x for x in (transcription, translation, abstract, incipit, annotations, critical_apparatus) if x),
        "named_people": named_people,
        "named_places": all_places,
        "organizations": organizations,
        "mentioned_entities": mentioned_entities,
        "repositories": unique(repositories),
        "archive_countries": unique(archive_countries),
        "archive_cities": unique(archive_cities),
        "shelfmarks": unique(shelfmarks),
        "witnesses": witnesses,
        "bibliography": bibliography,
        "hand_notes": hand_notes,
        "editor": editor,
        "authors": authors,
        "edition_status": edition_status,
        "revision_date": revision_date,
        "revision_who": revision_who,
        "facsimiles": graphic_urls,
        "has_images": bool(graphic_urls),
        "has_transcription": len(transcription.strip()) > 0,
        "has_translation": len(translation.strip()) > 0,
        "file": path.name,
        "url": url,
    }
    record["archive_labels"] = unique(repositories + archive_countries + archive_cities)
    record["shelfmark_labels"] = unique(shelfmarks)
    return record


def main() -> int:
    records: list[dict] = []
    errors: list[str] = []
    for path in sorted(REPO_ROOT.glob("*.xml"), key=lambda p: p.name.casefold()):
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as exc:
            errors.append(f"{path.name}: {exc}")
            continue
        if root.tag != f"{{{TEI_NS}}}TEI":
            continue
        if root.find(".//tei:correspDesc", NS) is None:
            continue
        records.append(make_record(path, root))

    OUTPUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Catálogo generado: {OUTPUT.relative_to(REPO_ROOT)} ({len(records)} cartas)")
    print(f"Con transcripción: {sum(bool(r['has_transcription']) for r in records)}; "
          f"con traducción: {sum(bool(r['has_translation']) for r in records)}; "
          f"con facsímil: {sum(bool(r['has_images']) for r in records)}.")
    if errors:
        print(f"Aviso: {len(errors)} archivo(s) no se pudieron leer:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
    if not records:
        print("No se encontraron XML-TEI con correspDesc.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
