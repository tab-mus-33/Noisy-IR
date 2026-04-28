"""
Builds TREC-format topic XML files from a list of query definitions.

Each topic has:
  - num:         integer topic ID
  - title:       short keyword query (what gets sent to the retrieval system)
  - description: longer natural-language statement of the information need
  - name_a:      primary material name variant used in the title query
  - name_b:      alternative name variant (used for Experiment 1 paired queries)

Experiment 1 requires paired topics: the same information need expressed using
two different name variants (e.g. "titania photocatalysis" vs "TiO2 photocatalysis").
Both should retrieve the same relevant documents.
"""

import xml.etree.ElementTree as ET
from pathlib import Path


# ---------------------------------------------------------------------------
# 30 topic pairs covering oxides, perovskites, superconductors, nitrides,
# carbides, 2D materials, battery materials, chalcogenides, and other ceramics.
# name_a = common/mineral/abbreviation name  (what a domain expert might search)
# name_b = formula or IUPAC name            (what a chemist or database uses)
# ---------------------------------------------------------------------------
TOPICS = [
    # ── Structural and functional oxides ────────────────────────────────────
    (
        1,
        "corundum", "Al2O3",
        "corundum thermal conductivity high temperature",
        "Find papers measuring or modelling the thermal conductivity of corundum at elevated temperatures.",
    ),
    (
        2,
        "titania", "TiO2",
        "titania photocatalysis water splitting",
        "Find papers on the photocatalytic activity of titania for solar-driven water splitting.",
    ),
    (
        3,
        "silica", "SiO2",
        "silica glass viscosity thermal",
        "Find papers on the viscosity or thermal properties of amorphous silica glass.",
    ),
    (
        4,
        "hematite", "Fe2O3",
        "hematite photoelectrochemical water oxidation",
        "Find papers on hematite as a photoanode for photoelectrochemical water oxidation.",
    ),
    (
        5,
        "magnetite", "Fe3O4",
        "magnetite nanoparticles magnetic hyperthermia",
        "Find papers on magnetite nanoparticles for magnetic hyperthermia cancer treatment.",
    ),
    (
        6,
        "zincite", "ZnO",
        "zincite piezoelectric nanowire nanogenerator",
        "Find papers on piezoelectric nanowires or nanogenerators based on zinc oxide.",
    ),
    (
        7,
        "cassiterite", "SnO2",
        "cassiterite gas sensor nitrogen dioxide",
        "Find papers on tin oxide resistive sensors for NO2 or other gas detection.",
    ),
    (
        8,
        "ceria", "CeO2",
        "ceria oxygen storage capacity catalyst",
        "Find papers on ceria as an oxygen storage material in three-way catalysts.",
    ),
    (
        9,
        "zirconia", "ZrO2",
        "zirconia thermal barrier coating turbine",
        "Find papers on yttria-stabilised zirconia thermal barrier coatings for turbine blades.",
    ),
    (
        10,
        "periclase", "MgO",
        "periclase sintering refractory",
        "Find papers on the sintering behaviour or refractory applications of periclase.",
    ),
    # ── Perovskites and complex oxides ──────────────────────────────────────
    (
        11,
        "barium titanate", "BaTiO3",
        "barium titanate piezoelectric energy harvesting",
        "Find papers on piezoelectric energy harvesting devices using barium titanate.",
    ),
    (
        12,
        "strontium titanate", "SrTiO3",
        "strontium titanate dielectric thin film",
        "Find papers on the dielectric properties of strontium titanate thin films.",
    ),
    (
        13,
        "bismuth ferrite", "BiFeO3",
        "bismuth ferrite multiferroic room temperature",
        "Find papers on multiferroic properties of bismuth ferrite at room temperature.",
    ),
    (
        14,
        "lead zirconate titanate", "PZT",
        "lead zirconate titanate actuator MEMS",
        "Find papers on PZT thin films for MEMS actuators or piezoelectric sensors.",
    ),
    (
        15,
        "lanthanum cuprate", "La2CuO4",
        "lanthanum cuprate antiferromagnetic parent compound",
        "Find papers on the antiferromagnetic order or doping of the cuprate parent compound.",
    ),
    # ── Superconductors ─────────────────────────────────────────────────────
    (
        16,
        "YBCO", "YBa2Cu3O7",
        "YBCO flux pinning critical current density",
        "Find papers on flux pinning mechanisms and critical current enhancement in YBCO.",
    ),
    (
        17,
        "BSCCO", "Bi2Sr2CaCu2O8",
        "BSCCO Josephson junction intrinsic",
        "Find papers on intrinsic Josephson junctions in Bi-2212 high-temperature superconductors.",
    ),
    # ── Nitrides ────────────────────────────────────────────────────────────
    (
        18,
        "hexagonal boron nitride", "h-BN",
        "hexagonal boron nitride dielectric substrate graphene",
        "Find papers using hexagonal boron nitride as a dielectric substrate for graphene devices.",
    ),
    (
        19,
        "gallium nitride", "GaN",
        "gallium nitride high electron mobility transistor power",
        "Find papers on GaN HEMTs for high-power or high-frequency electronic applications.",
    ),
    (
        20,
        "silicon nitride", "Si3N4",
        "silicon nitride fracture toughness structural ceramic",
        "Find papers on the fracture toughness or mechanical reliability of silicon nitride ceramics.",
    ),
    # ── Carbides ────────────────────────────────────────────────────────────
    (
        21,
        "carborundum", "SiC",
        "carborundum wide bandgap power semiconductor",
        "Find papers on silicon carbide as a wide-bandgap semiconductor for power electronics.",
    ),
    (
        22,
        "tungsten carbide", "WC",
        "tungsten carbide hardness wear-resistant coating",
        "Find papers on the hardness or tribological performance of tungsten carbide coatings.",
    ),
    # ── 2D materials ────────────────────────────────────────────────────────
    (
        23,
        "monolayer graphene", "single-layer graphene",
        "monolayer graphene electron mobility charge transport",
        "Find papers on the electronic mobility or charge transport in monolayer graphene.",
    ),
    (
        24,
        "molybdenite", "MoS2",
        "molybdenite field-effect transistor two-dimensional",
        "Find papers on MoS2 as a two-dimensional semiconductor in field-effect transistors.",
    ),
    (
        25,
        "tungstenite", "WS2",
        "tungstenite photoluminescence valley polarization",
        "Find papers on photoluminescence or valley polarisation in monolayer WS2.",
    ),
    # ── Battery materials ────────────────────────────────────────────────────
    (
        26,
        "lithium iron phosphate", "LFP",
        "lithium iron phosphate cathode cycle stability capacity",
        "Find papers on the cycle stability or capacity retention of LFP cathode materials.",
    ),
    (
        27,
        "NMC", "lithium nickel manganese cobalt oxide",
        "NMC high-voltage cathode lithium-ion battery",
        "Find papers on high-voltage performance or degradation of NMC cathode materials.",
    ),
    # ── Chalcogenides and optoelectronics ───────────────────────────────────
    (
        28,
        "galena", "PbS",
        "galena quantum dot infrared photodetector",
        "Find papers on lead sulfide quantum dots for infrared photodetection.",
    ),
    (
        29,
        "greenockite", "CdS",
        "greenockite thin film solar cell heterojunction",
        "Find papers on CdS as a buffer layer in thin-film solar cell heterojunctions.",
    ),
    # ── Transparent conductors ───────────────────────────────────────────────
    (
        30,
        "indium tin oxide", "ITO",
        "indium tin oxide transparent electrode thin film",
        "Find papers on ITO as a transparent conducting electrode in optoelectronic devices.",
    ),
]


def build_topics_xml(
    topics: list[tuple],
    output_path: str | Path,
    variant: str = "a",
) -> None:
    """
    Write a TREC-format topics XML file.

    Parameters
    ----------
    topics      : list of (num, name_a, name_b, title_a, description) tuples
    output_path : where to write the XML
    variant     : 'a' to use name_a in title, 'b' to substitute name_b
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    root = ET.Element("topics")

    for num, name_a, name_b, title_a, description in topics:
        if variant == "a":
            title = title_a
        else:
            title = title_a.replace(name_a, name_b)

        top = ET.SubElement(root, "top")
        ET.SubElement(top, "num").text = str(num)
        ET.SubElement(top, "title").text = title
        ET.SubElement(top, "description").text = description

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=False)
    print(f"Wrote {len(topics)} topics ({variant=}) to {output_path}")


def build_paired_topics(
    topics: list[tuple],
    output_dir: str | Path,
) -> tuple[Path, Path]:
    """
    Write both name_a and name_b variants for Experiment 1.

    Returns paths to (topics_a.xml, topics_b.xml).
    """
    output_dir = Path(output_dir)
    path_a = output_dir / "matsci_topics_a.xml"
    path_b = output_dir / "matsci_topics_b.xml"
    build_topics_xml(topics, path_a, variant="a")
    build_topics_xml(topics, path_b, variant="b")
    return path_a, path_b


if __name__ == "__main__":
    from matsci.config import CONFIG

    path_a, path_b = build_paired_topics(
        TOPICS,
        output_dir=Path(CONFIG["topics_xml"]).parent,
    )
    print(f"\nName-A topics: {path_a}")
    print(f"Name-B topics: {path_b}")
