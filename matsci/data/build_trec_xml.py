"""
Converts a list of document dicts into TREC-XML format for PyTerrier indexing.

Analogous to converter.py from the original thesis, but for materials science
papers rather than podcast transcripts. Each paper becomes one document (no
time-window segmentation needed — abstracts are already a natural unit).
"""

import html
import json
from pathlib import Path
from typing import Iterable


def _escape(text: str) -> str:
    return html.escape(str(text), quote=False)


def docs_to_trec_xml(
    documents: Iterable[dict],
    output_path: str | Path,
    docno_field: str = "docno",
    text_fields: list[str] = ("title", "abstract"),
) -> int:
    """
    Write documents to a TREC-XML file.

    Parameters
    ----------
    documents   : iterable of dicts; must contain docno_field and all text_fields
    output_path : where to write the .xml file
    docno_field : key in each dict used as the document identifier
    text_fields : keys whose values are concatenated as the document body

    Returns
    -------
    Number of documents written
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    count = 0
    with open(output_path, "w", encoding="utf-8") as f:
        for doc in documents:
            docno = _escape(str(doc[docno_field]))
            body_parts = [str(doc.get(field, "")) for field in text_fields]
            body = _escape(" ".join(p for p in body_parts if p))

            f.write(f"<DOC>\n")
            f.write(f"<DOCNO>{docno}</DOCNO>\n")
            f.write(f"<TEXT>{body}</TEXT>\n")
            f.write(f"</DOC>\n")
            count += 1

    return count


def jsonl_to_trec_xml(
    jsonl_path: str | Path,
    output_path: str | Path,
    docno_field: str = "docno",
    text_fields: list[str] = ("title", "abstract"),
) -> int:
    """Convenience wrapper: read a .jsonl file and write TREC-XML."""
    def _iter():
        with open(jsonl_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    return docs_to_trec_xml(_iter(), output_path, docno_field, text_fields)


if __name__ == "__main__":
    # Smoke test with synthetic documents
    sample_docs = [
        {
            "docno": "arxiv_2301.00001",
            "title": "Thermal properties of α-Al₂O₃ corundum at high temperature",
            "abstract": (
                "We report thermal conductivity measurements of corundum (α-Al₂O₃) "
                "between 300 K and 1800 K. The alumina samples were prepared by "
                "solid-state sintering. Results show a monotonic decrease consistent "
                "with phonon-phonon scattering."
            ),
        },
        {
            "docno": "arxiv_2301.00002",
            "title": "Photocatalytic activity of TiO2 polymorphs",
            "abstract": (
                "Rutile and anatase titanium dioxide (TiO2) are compared as "
                "photocatalysts for water splitting. Anatase shows higher activity "
                "under UV illumination due to its larger band gap."
            ),
        },
    ]

    n = docs_to_trec_xml(sample_docs, "/tmp/test_corpus.xml")
    print(f"Wrote {n} documents to /tmp/test_corpus.xml")

    with open("/tmp/test_corpus.xml") as f:
        print(f.read())
