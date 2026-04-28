"""
Retrieves canonical formula and common name variants from the Materials Project.

Used for inorganic crystalline materials where PubChem coverage is weaker.
Requires MP_API_KEY environment variable (set in .env).

For a given material name, returns:
  - canonical reduced formula (e.g. "Al2O3")
  - pretty formula (e.g. "Al₂O₃")
  - common names from the MP database
  - IDs of associated papers (used for qrels construction)
"""

from mp_api.client import MPRester

from matsci.config import CONFIG


def _get_client() -> MPRester:
    key = CONFIG["matproject_api_key"]
    if not key:
        raise EnvironmentError(
            "MP_API_KEY not set. Add it to your .env file:\n"
            "  MP_API_KEY=your_key_here"
        )
    return MPRester(key)


def formula_to_synonyms(formula: str) -> list[str]:
    """
    Given a formula or material name, return formula variants from Materials Project.

    Returns e.g. ["Al2O3", "Al₂O₃"] for "alumina".
    """
    synonyms: list[str] = []
    try:
        with _get_client() as mpr:
            results = mpr.materials.summary.search(
                formula=formula,
                fields=["formula_pretty", "formula_anonymous", "chemsys"],
            )
            for r in results[:5]:  # avoid over-fetching
                if r.formula_pretty and r.formula_pretty not in synonyms:
                    synonyms.append(r.formula_pretty)
                # Add ASCII version without subscript unicode
                ascii_formula = r.formula_pretty.translate(
                    str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
                )
                if ascii_formula not in synonyms:
                    synonyms.append(ascii_formula)
    except Exception as e:
        print(f"  Materials Project lookup failed for '{formula}': {e}")

    return synonyms


def get_papers_for_material(material_id: str) -> list[str]:
    """
    Return DOIs of papers associated with a Materials Project material entry.

    Used in evaluation/build_qrels.py to construct relevance judgements.
    """
    dois: list[str] = []
    try:
        with _get_client() as mpr:
            # References field contains associated paper DOIs
            results = mpr.materials.summary.search(
                material_ids=[material_id],
                fields=["origins"],
            )
            for r in results:
                if hasattr(r, "origins") and r.origins:
                    for origin in r.origins:
                        if hasattr(origin, "name") and origin.name:
                            dois.append(origin.name)
    except Exception as e:
        print(f"  Could not fetch papers for {material_id}: {e}")
    return dois


if __name__ == "__main__":
    test_formulas = ["Al2O3", "TiO2", "BaTiO3", "SnO2"]
    for formula in test_formulas:
        syns = formula_to_synonyms(formula)
        print(f"\n{formula}: {syns}")
