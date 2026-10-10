#!/usr/bin/env python3
"""Build a faceted search catalogue from CoBAM TEI-XML correspondence files."""
from __future__ import annotations

import json
import re
import sys
import unicodedata
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


def normalize_language_label(value: str | None) -> str:
    """Normalize the display label of a language without changing its spelling."""
    label = clean(value)
    return label[:1].upper() + label[1:] if label else ""


def normalize_origin_label(value: str | None) -> str:
    """Use one preferred Spanish form for Cleves/Kleve in origin filters."""
    label = clean(value)
    key = unicodedata.normalize("NFD", label).encode("ascii", "ignore").decode("ascii").casefold()
    if key in {"cleves", "cleveris"}:
        return "Cléveris"
    return label



def normalize_repository_label(value: str | None) -> str:
    """Unify the bilingual archive name used by CoBAM repository filters."""
    label = clean(value)
    key = unicodedata.normalize("NFD", label).encode("ascii", "ignore").decode("ascii").casefold()
    if key in {
        "algemeen rijksarchief",
        "algemeen rijgsarchief",
        "archives generales du royaume/algemeen rijksarchief",
    }:
        return "Archives Générales du Royaume/Algemeen Rijksarchief"
    return label

def normalize_archive_city_label(value: str | None) -> str:
    """Use the preferred Spanish name for archive localities in facets."""
    label = clean(value)
    key = unicodedata.normalize("NFD", label).encode("ascii", "ignore").decode("ascii").casefold()
    if key in {"brussels", "bruselas"}:
        return "Bruselas"
    return label


def normalize_archive_country_label(value: str | None) -> str:
    """Use the preferred Spanish country name in archive-country facets."""
    label = clean(value)
    key = unicodedata.normalize("NFD", label).encode("ascii", "ignore").decode("ascii").casefold()
    if key in {"belgium", "belgica"}:
        return "Bélgica"
    if key in {"netherlands", "paises bajos"}:
        return "Países Bajos"
    return label

def normalize_person_label(value: str | None) -> str:
    """Normalize known correspondent-name variants, preserving hypothetical brackets."""
    label = clean(value)
    key = unicodedata.normalize("NFD", label).encode("ascii", "ignore").decode("ascii").casefold()
    if key in {"maxiiliano morillon", "maximiiano morillon"}:
        return "Maximiliano Morillon"
    if key in {"[cornelio gema frisio]", "[cornelio gemma frisio]"}:
        return "[Cornelio Gema Frisio]"
    if key in {"cornelio gema", "cornelio gemma", "cornelio gema frisio", "cornelio gemma frisio"}:
        return "Cornelio Gema Frisio"
    return label


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


def date_attribute_years(date_el: ET.Element | None) -> list[int]:
    if date_el is None:
        return []
    values = [
        date_el.get(attr, "")
        for attr in ("from", "notBefore", "when", "to", "notAfter", "until")
        if date_el.get(attr)
    ]
    return [int(year) for value in values for year in re.findall(r"\b(?:15|16)\d{2}\b", value)]


def visible_date_years(date_el: ET.Element | None, title: str, filename: str) -> list[int]:
    # Prefer the human-readable date/title before the filename convention.
    for source in (text_of(date_el), title, filename):
        years = [int(y) for y in re.findall(r"\b(?:15|16)\d{2}\b", source)]
        if years:
            return years
    return []


def date_warning(date_el: ET.Element | None, title: str, filename: str) -> str:
    explicit = date_attribute_years(date_el)
    visible = visible_date_years(date_el, title, filename)
    if explicit and visible and not set(explicit).intersection(visible):
        attrs = ", ".join(
            f"{name}={date_el.get(name)}"
            for name in ("from", "notBefore", "when", "to", "notAfter", "until")
            if date_el is not None and date_el.get(name)
        )
        visible_years = ", ".join(map(str, sorted(set(visible))))
        return (
            f"El año normalizado en TEI ({attrs}) no coincide con la fecha legible "
            f"en el título o el identificador ({visible_years}). Conviene revisar el XML."
        )
    return ""


def get_years(date_el: ET.Element | None, title: str, filename: str) -> tuple[int | None, int | None]:
    explicit = date_attribute_years(date_el)
    visible = visible_date_years(date_el, title, filename)
    # If the encoded date contradicts the published human-readable date, use the
    # latter for the prototype's year facets, but preserve and flag the conflict.
    if explicit and visible:
        if not set(explicit).intersection(visible):
            return min(visible), max(visible)
        return min(explicit), max(explicit)
    values = explicit or visible
    if values:
        return min(values), max(values)
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
    if body is None:
        return plain_tei_text(text_el)
    # Index all textual blocks, including address/marginal material, openers
    # and closers, without duplicating critical readings.
    block_tags = {"p", "ab", "opener", "closer", "salute", "signed", "dateline"}
    blocks = [
        clean(plain_tei_text(node))
        for node in body.iter()
        if local_name(node) in block_tags
    ]
    blocks = [block for block in blocks if block]
    return "\n\n".join(blocks) if blocks else clean(plain_tei_text(body))



def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def plain_tei_text(element: ET.Element | None, mode: str = "clean") -> str:
    """Extract reading text without duplicating alternative readings."""
    if element is None:
        return ""
    kind = local_name(element)
    if kind == "app":
        choice = element.find("tei:lem", NS)
        return plain_tei_text(choice if choice is not None else next(iter(element), None), mode)
    if kind == "choice":
        priority = ("corr", "reg", "expan", "orig", "sic") if mode == "clean" else ("sic", "orig", "corr", "reg", "expan")
        selected = next((element.find(f"tei:{name}", NS) for name in priority if element.find(f"tei:{name}", NS) is not None), None)
        return plain_tei_text(selected if selected is not None else next(iter(element), None), mode)
    if kind == "pb":
        return ""
    parts = [element.text or ""]
    for child in list(element):
        parts.append(plain_tei_text(child, mode))
        parts.append(child.tail or "")
    return clean("".join(parts))


def html_escape(value: str | None) -> str:
    from html import escape
    return escape(value or "", quote=True)


def tei_inline_html(
    element: ET.Element | None,
    *,
    mode: str,
    facsimile_map: dict[str, str],
    apparatus: list[dict[str, str]],
    allow_page_links: bool = True,
) -> str:
    """Render a safe, deliberately small TEI subset as HTML for the reader view.

    The HTML is generated here from known TEI tags; source text and attributes are
    escaped, and only HTTP(S) targets from the catalogue are emitted as links.
    """
    if element is None:
        return ""
    kind = local_name(element)

    def children(el: ET.Element) -> str:
        result = html_escape(el.text)
        for child in list(el):
            result += tei_inline_html(
                child, mode=mode, facsimile_map=facsimile_map,
                apparatus=apparatus, allow_page_links=allow_page_links,
            )
            result += html_escape(child.tail)
        return result

    if kind == "pb":
        label = element.get("n", "Salto de página")
        target = element.get("facs", "").lstrip("#")
        url = facsimile_map.get(target, "")
        if allow_page_links and url.startswith(("https://", "http://")):
            href = html_escape(url)
            return f'<span class="tei-pagebreak"><a href="{href}" target="_blank" rel="noopener noreferrer">{html_escape("[" + label + "]")}</a></span>'
        return f'<span class="tei-pagebreak">{html_escape("[" + label + "]")}</span>'

    if kind == "app":
        lem = element.find("tei:lem", NS)
        lemma_html = tei_inline_html(lem, mode=mode, facsimile_map=facsimile_map, apparatus=apparatus) if lem is not None else children(element)
        lemma_text = plain_tei_text(lem) if lem is not None else plain_tei_text(element)
        readings = []
        for rdg in element.findall("tei:rdg", NS):
            readings.append({
                "text": plain_tei_text(rdg),
                "witness": rdg.get("wit", "").replace("#", "").strip(),
            })
        witness = lem.get("wit", "") if lem is not None else ""
        if mode == "clean":
            return lemma_html
        number = len(apparatus) + 1
        apparatus.append({
            "id": f"app-{number}",
            "number": str(number),
            "lemma": lemma_text,
            "lemma_witness": witness.replace("#", "").strip(),
            "readings": readings,
        })
        return f'<span class="tei-app-lemma">{lemma_html}<sup><a href="#apparatus-{number}" aria-label="Variante {number}">[{number}]</a></sup></span>'

    if kind == "choice":
        if mode == "clean":
            priority = ("corr", "reg", "expan", "orig", "sic")
            selected = next((element.find(f"tei:{n}", NS) for n in priority if element.find(f"tei:{n}", NS) is not None), None)
            return tei_inline_html(selected, mode=mode, facsimile_map=facsimile_map, apparatus=apparatus) if selected is not None else children(element)
        sic = element.find("tei:sic", NS)
        corr = element.find("tei:corr", NS)
        orig = element.find("tei:orig", NS)
        reg = element.find("tei:reg", NS)
        if sic is not None or corr is not None:
            left = tei_inline_html(sic, mode=mode, facsimile_map=facsimile_map, apparatus=apparatus) if sic is not None else ""
            right = tei_inline_html(corr, mode=mode, facsimile_map=facsimile_map, apparatus=apparatus) if corr is not None else ""
            return f'<span class="tei-choice">{left}{right}</span>'
        selected = orig if orig is not None else reg
        return tei_inline_html(selected, mode=mode, facsimile_map=facsimile_map, apparatus=apparatus) if selected is not None else children(element)

    if kind == "ref":
        target = element.get("target", "")
        label = children(element)
        xml_id = element.get(f"{{{XML_NS}}}id", "")
        anchor = f' id="ref-{html_escape(xml_id)}"' if xml_id else ""
        if target.startswith("#"):
            target_id = target[1:]
            if target_id.startswith("note"):
                return f'<sup class="tei-note-ref"{anchor}><a href="#note-{html_escape(target_id)}">{label}</a></sup>'
            if target_id.startswith("reference"):
                return f'<a class="tei-note-backlink"{anchor} href="#ref-{html_escape(target_id)}">{label}</a>'
        if target.startswith(("https://", "http://")):
            return f'<a{anchor} href="{html_escape(target)}" target="_blank" rel="noopener noreferrer">{label}</a>'
        return f'<span{anchor}>{label}</span>'

    if kind == "expan":
        content = children(element)
        return content if mode == "clean" else f'<span class="tei-expansion" title="Expansión editorial">{content}</span>'
    if kind == "ex":
        content = children(element)
        return content if mode == "clean" else f'<span class="tei-ex">{content}</span>'
    if kind == "sic":
        return f'<span class="tei-sic">{children(element)}</span>'
    if kind == "corr":
        content = children(element)
        return content if mode == "clean" else f'<span class="tei-corr">{content}</span>'
    if kind == "orig":
        content = children(element)
        return content if mode == "clean" else f'<span class="tei-orig">{content}</span>'
    if kind == "reg":
        content = children(element)
        return content if mode == "clean" else f'<span class="tei-reg">{content}</span>'
    if kind == "supplied":
        content = children(element)
        return content if mode == "clean" else f'<span class="tei-supplied" title="Texto suplido editorialmente">⟨{content}⟩</span>'
    if kind == "del":
        return "" if mode == "clean" else f'<del>{children(element)}</del>'
    if kind == "add":
        content = children(element)
        return content if mode == "clean" else f'<ins class="tei-add">{content}</ins>'
    if kind == "unclear":
        content = children(element)
        return content if mode == "clean" else f'<span class="tei-unclear" title="Lectura dudosa">{content}</span>'
    if kind == "gap":
        reason = element.get("reason", "ilegible")
        return f'<span class="tei-gap" title="Laguna textual">[{html_escape(reason)}]</span>'
    if kind == "name":
        content = children(element)
        if mode == "clean":
            return content
        entity_type = element.get("type", "entidad")
        return f'<span class="tei-entity tei-entity-{html_escape(entity_type)}" title="{html_escape(entity_type)}">{content}</span>'
    if kind == "date":
        when = element.get("when", "")
        title = f' title="{html_escape(when)}"' if when and mode != "clean" else ""
        return f'<span class="tei-date"{title}>{children(element)}</span>'
    if kind == "hi":
        rend = element.get("rend", "")
        if "bold" in rend.lower():
            return f'<strong>{children(element)}</strong>'
        if "italic" in rend.lower():
            return f'<em>{children(element)}</em>'
        if "underline" in rend.lower():
            return f'<span class="tei-hi-underline">{children(element)}</span>'
        return f'<span class="tei-hi">{children(element)}</span>'
    if kind in {"title", "foreign", "mentioned"}:
        return f'<em>{children(element)}</em>' if kind == "title" else children(element)
    if kind in {"p", "ab"}:
        return f'<p>{children(element)}</p>'
    if kind in {"opener", "closer", "salute", "signed", "dateline"}:
        return f'<div class="tei-{kind}">{children(element)}</div>'
    if kind == "head":
        content = plain_tei_text(element)
        if not content:
            return ""
        return f'<h4>{children(element)}</h4>'
    if kind == "lb":
        return "<br/>"
    if kind == "note":
        if element.get("type") == "footnote":
            return ""
        return f'<span class="tei-inline-note">{children(element)}</span>'
    if kind == "div":
        div_type = element.get("type", "")
        head = element.find("tei:head", NS)
        label = tei_inline_html(head, mode=mode, facsimile_map=facsimile_map, apparatus=apparatus) if head is not None else ""
        inner = html_escape(element.text)
        for child in list(element):
            if child is head:
                inner += html_escape(child.tail)
                continue
            inner += tei_inline_html(child, mode=mode, facsimile_map=facsimile_map, apparatus=apparatus)
            inner += html_escape(child.tail)
        cls = f"tei-block tei-block-{div_type}" if div_type else "tei-block"
        heading = f'<h3>{label}</h3>' if label else ""
        return f'<section class="{html_escape(cls)}">{heading}{inner}</section>'
    if kind in {"body", "front", "back", "text", "group", "listWit", "witness"}:
        return children(element)
    return children(element)



def tei_contents_html(
    element: ET.Element,
    *,
    mode: str,
    facsimile_map: dict[str, str],
    apparatus: list[dict],
) -> str:
    """Render an element's children without treating its own tag as a wrapper."""
    result = html_escape(element.text)
    for child in list(element):
        result += tei_inline_html(child, mode=mode, facsimile_map=facsimile_map, apparatus=apparatus)
        result += html_escape(child.tail)
    return result


def source_details(root: ET.Element, source_el: ET.Element | None, translation_el: ET.Element | None) -> dict:
    graphics: dict[str, str] = {}
    for graphic in root.findall(".//tei:facsimile/tei:graphic", NS):
        xml_id = graphic.get(f"{{{XML_NS}}}id", "")
        url = clean(graphic.get("url", ""))
        if xml_id and url.startswith(("https://", "http://")):
            graphics[xml_id] = url

    source_body = source_el.find("tei:body", NS) if source_el is not None else None
    translation_body = translation_el.find("tei:body", NS) if translation_el is not None else None
    source_front = source_el.find("tei:front", NS) if source_el is not None else None

    commentary_html, _ = render_tei_fragment(source_front, root, "clean")
    commentary = clean(" ".join(plain_tei_text(p) for p in source_front.findall(".//tei:p", NS))) if source_front is not None else ""
    source_marked_html, apparatus = render_tei_fragment(source_body, root, "marked")
    source_clean_html, _ = render_tei_fragment(source_body, root, "clean")
    translation_html, _ = render_tei_fragment(translation_body, root, "clean")

    footnotes = []
    for note in root.findall(".//tei:back//tei:note[@type='footnote']", NS):
        note_id = note.get(f"{{{XML_NS}}}id", "")
        footnotes.append({
            "id": note_id,
            "text": plain_tei_text(note),
            "html": tei_contents_html(note, mode="clean", facsimile_map=graphics, apparatus=[]),
        })

    facsimile_items = extract_facsimile_items(root, graphics)
    return {
        "commentary": commentary,
        "commentary_html": commentary_html,
        "source_marked_html": source_marked_html,
        "source_clean_html": source_clean_html,
        "translation_html": translation_html,
        "apparatus": apparatus,
        "footnotes": footnotes,
        "facsimile_items": facsimile_items,
        "has_apparatus": bool(apparatus),
        "has_footnotes": bool(footnotes),
    }


def extract_facsimile_items(root: ET.Element, facsimile_map: dict[str, str]) -> list[dict[str, str]]:
    # Use the order of <facsimile>/<graphic> as the default gallery sequence,
    # while resolving each item's folio label through <pb facs="#..."/>.
    labels: dict[str, str] = {}
    for page in root.findall(".//tei:text//tei:pb[@facs]", NS):
        target = page.get("facs", "").lstrip("#")
        if target and target not in labels:
            labels[target] = page.get("n", target)
    return [
        {
            "id": graphic_id,
            "url": url,
            "label": labels.get(graphic_id, f"Imagen {index+1}"),
        }
        for index, (graphic_id, url) in enumerate(facsimile_map.items())
        if url
    ]


def render_tei_fragment(element: ET.Element | None, root: ET.Element, mode: str) -> tuple[str, list[dict[str, str]]]:
    graphics: dict[str, str] = {}
    for graphic in root.findall(".//tei:facsimile/tei:graphic", NS):
        xml_id = graphic.get(f"{{{XML_NS}}}id", "")
        url = graphic.get("url", "")
        if url.startswith("http://lacorrespondenciadebenitoariasmontano.online/"):
            url = url.replace("http://", "https://", 1)
        if xml_id and url.startswith(("https://", "http://")):
            graphics[xml_id] = url
    apparatus: list[dict[str, str]] = []
    rendered = tei_inline_html(element, mode=mode, facsimile_map=graphics, apparatus=apparatus)
    return rendered, apparatus

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
    sender = normalize_person_label(sender)
    origin = normalize_origin_label(origin)
    recipient, destination = action_info(root, "received")
    recipient = normalize_person_label(recipient)
    abstract = first_text(root, ".//tei:note[@type='abstract']")
    incipit = first_text(root, ".//tei:note[@type='incipit']")
    language_elements = root.findall(".//tei:langUsage/tei:language", NS)
    languages = unique([normalize_language_label(text_of(el)) for el in language_elements])
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
    chronology_warning = date_warning(date_el, title, path.name)

    source_el = root.find(".//tei:text[@type='source']", NS)
    if source_el is None:
        source_el = root.find(".//tei:text[tei:body]", NS)
    transcription = body_text(source_el)
    translation_el = root.find(".//tei:text[@type='translation']", NS)
    translation = body_text(translation_el)
    reader_details = source_details(root, source_el, translation_el)
    # Index editorial notes and variants for the free-text search as well as for
    # the dedicated reader view.
    notes_in_text = unique([text_of(n) for n in root.findall(".//tei:text//tei:note", NS)])
    apparatus_entries = unique([text_of(a) for a in root.findall(".//tei:text//tei:app", NS)])
    critical_apparatus = " ".join(apparatus_entries)
    annotations = " ".join(notes_in_text + apparatus_entries)
    commentary = reader_details["commentary"]

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
        repository = normalize_repository_label(text_of(ms_identifier.find("tei:msName", NS))) if ms_identifier is not None else ""
        city = normalize_archive_city_label(text_of(ms_identifier.find("tei:settlement", NS))) if ms_identifier is not None else ""
        country = normalize_archive_country_label(text_of(ms_identifier.find("tei:country", NS))) if ms_identifier is not None else ""
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
        clean(el.get("url")).replace("http://lacorrespondenciadebenitoariasmontano.online/", "https://lacorrespondenciadebenitoariasmontano.online/", 1) for el in root.findall(".//tei:facsimile/tei:graphic", NS)
        if el.get("url")
    ])
    bibliography = unique([
        text_of(el) for el in root.findall(".//tei:sourceDesc/tei:bibl[@type='inextenso']", NS)
    ])
    hand_notes = unique([text_of(el) for el in root.findall(".//tei:handNotes/tei:handNote", NS)])
    editor = first_text(root, ".//tei:fileDesc/tei:titleStmt/tei:editor")
    authors = unique([text_of(el) for el in root.findall(".//tei:fileDesc/tei:titleStmt/tei:author", NS)])
    editorial_responsibility = first_text(root, ".//tei:fileDesc/tei:titleStmt/tei:respStmt/tei:resp")
    responsible_person = first_text(root, ".//tei:fileDesc/tei:titleStmt/tei:respStmt/tei:name")
    revision = root.find(".//tei:revisionDesc", NS)
    edition_status = revision.get("status", "") if revision is not None else ""
    changes = root.findall(".//tei:revisionDesc/tei:change", NS)
    last_change = changes[-1] if changes else None
    revision_date = last_change.get("when", "") if last_change is not None else ""
    revision_who = last_change.get("who", "") if last_change is not None else ""

    url = "https://github.com/CoBAM-editor/CoBAM/blob/main/" + quote(path.name, safe="")
    clean_letter_code = letter_code.strip(" []").strip()
    # Only emit a published permalink when it has been explicitly verified.
    # WordPress slugs are not reliably derivable from the date in the TEI.
    # Map by exact source filename, not just date/letter code: supplementary
    # XML files (e.g. "Libros") can share the same CoBAM identifier.
    # Add entries only after checking the live published edition page.
    published_url_overrides = {
        "1560 02 01-60 05 05 CoBAM.xml": "https://lacorrespondenciadebenitoariasmontano.online/es_es/1560-02-01-1560-05-05/",
        "1568 07 22 CoBAM.xml": "https://lacorrespondenciadebenitoariasmontano.online/es_es/correspondencia/1568-07-20/",
        "1568 08 07 CoBAM.xml": "https://lacorrespondenciadebenitoariasmontano.online/es_es/correspondencia/15680807-2/",
        "1568 08 29 CoBAM.xml": "https://lacorrespondenciadebenitoariasmontano.online/es_es/1568-08-29/",
        "1569 04 06 CoBAM.xml": "https://lacorrespondenciadebenitoariasmontano.online/es_es/1569-04-06/",
        "1570 05 00 Z CoBAM.xml": "https://lacorrespondenciadebenitoariasmontano.online/es_es/1570-05-00-z/",
    }
    published_url = published_url_overrides.get(path.name, "")
    record = {
        # Use the source filename as a unique catalogue key. Preserve xml:id
        # separately: legacy TEI identifiers can repeat across related files.
        "id": path.stem,
        "tei_id": xml_id,
        "letter_code": letter_code.strip(" []") or xml_id or path.stem,
        "title": title,
        "date": date_label or letter_code or path.stem,
        "date_when": date_when,
        "date_from": date_from,
        "date_to": date_to,
        "date_certainty": date_certainty,
        "date_warning": chronology_warning,
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
        "commentary": commentary,
        "commentary_html": reader_details["commentary_html"],
        "incipit": incipit,
        "transcription": transcription,
        "translation": translation,
        "source_marked_html": reader_details["source_marked_html"],
        "source_clean_html": reader_details["source_clean_html"],
        "translation_html": reader_details["translation_html"],
        "apparatus": reader_details["apparatus"],
        "footnotes": reader_details["footnotes"],
        "facsimile_items": reader_details["facsimile_items"],
        "has_apparatus": reader_details["has_apparatus"],
        "has_footnotes": reader_details["has_footnotes"],
        "annotations": annotations,
        "critical_apparatus": critical_apparatus,
        "text": " ".join(x for x in (transcription, translation, abstract, commentary, incipit, annotations, critical_apparatus) if x),
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
        "editorial_responsibility": editorial_responsibility,
        "responsible_person": responsible_person,
        "edition_status": edition_status,
        "revision_date": revision_date,
        "revision_who": revision_who,
        "facsimiles": graphic_urls,
        "has_images": bool(graphic_urls),
        "has_transcription": len(transcription.strip()) > 0,
        "has_translation": len(translation.strip()) > 0,
        "file": path.name,
        "url": url,
        "published_url": published_url,
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
