"""
Simulates OCR degradation on clean text at a specified character error rate.

OCR errors modelled here reflect real failure modes on materials science text:
- 0/O and 1/l/I confusion (especially damaging to chemical formulas)
- Subscript digit loss or garbling (TiO2 -> Ti02 or TiO 2)
- Greek letter mangling (α -> a, β -> b)
- Hyphen and dash removal
- Random character substitution for general degradation
"""

import random
import re
import string


# Character-level confusion pairs observed in materials science OCR
_OCR_CONFUSIONS = {
    "0": ["O", "o", "Q"],
    "O": ["0", "o"],
    "o": ["0", "O"],
    "1": ["l", "I", "i", "|"],
    "l": ["1", "I"],
    "I": ["1", "l"],
    "2": ["Z", "z"],
    "5": ["S", "s"],
    "6": ["b", "G"],
    "8": ["B"],
    "B": ["8"],
    "α": ["a", "cx"],
    "β": ["b", "13"],
    "γ": ["y", "v"],
    "δ": ["d", "5"],
    "μ": ["u", "p"],
    "Å": ["A"],
    "-": ["", " "],     # hyphens dropped or spaced — breaks hyphenated compounds
    "·": ["."],
}

# Subscript unicode digits -> ASCII (formula corruption)
_SUBSCRIPT_MAP = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")


def simulate_ocr_noise(text: str, error_rate: float, seed: int = 42) -> str:
    """
    Corrupt text to simulate OCR errors at the given character error rate.

    Parameters
    ----------
    text       : input clean text
    error_rate : fraction of characters to corrupt (0.0 = no change, 0.3 = 30%)
    seed       : random seed for reproducibility

    Returns
    -------
    Corrupted text string
    """
    if error_rate == 0.0:
        return text

    rng = random.Random(seed)
    chars = list(text)
    n_errors = max(1, int(len(chars) * error_rate))
    positions = rng.sample(range(len(chars)), min(n_errors, len(chars)))

    for pos in positions:
        ch = chars[pos]
        if ch in _OCR_CONFUSIONS and rng.random() < 0.6:
            # Apply a known confusion substitution
            chars[pos] = rng.choice(_OCR_CONFUSIONS[ch])
        elif ch.isalpha() and rng.random() < 0.3:
            # Random character deletion
            chars[pos] = ""
        elif ch.isalpha() and rng.random() < 0.1:
            # Random character substitution
            chars[pos] = rng.choice(string.ascii_lowercase)

    result = "".join(chars)

    # Normalise subscript unicode to ASCII (common OCR pre-processing artifact)
    result = result.translate(_SUBSCRIPT_MAP)

    return result


def corrupt_corpus(
    documents: list[dict],
    error_rate: float,
    text_field: str = "text",
    seed: int = 42,
) -> list[dict]:
    """
    Apply OCR noise to a list of document dicts, returning corrupted copies.

    Parameters
    ----------
    documents  : list of dicts with at least 'docno' and text_field keys
    error_rate : character error rate to apply
    text_field : key in each dict containing the text to corrupt
    seed       : random seed

    Returns
    -------
    New list of dicts with corrupted text; docno is preserved unchanged
    """
    corrupted = []
    for i, doc in enumerate(documents):
        new_doc = dict(doc)
        new_doc[text_field] = simulate_ocr_noise(doc[text_field], error_rate, seed=seed + i)
        corrupted.append(new_doc)
    return corrupted


if __name__ == "__main__":
    sample = (
        "The α-Al₂O₃ (corundum) phase shows high thermal stability. "
        "Rutile TiO2 and anatase TiO2 are the two most common polymorphs "
        "of titanium dioxide used in photocatalysis."
    )
    for rate in [0.0, 0.05, 0.10, 0.20, 0.30]:
        print(f"\nerror_rate={rate:.0%}:")
        print(simulate_ocr_noise(sample, rate))
