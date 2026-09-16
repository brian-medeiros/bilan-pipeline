"""All domain mappings and interpretation decisions in one place.

The official notes govern ambiguous capital/cash/depreciation labels. The emitted
cash measure is disponibilites; VMP is retained as supplemental evidence, not
automatically treated as a cash equivalent. COGS follows the literal additive
French label, with every printed component required (no blank-to-zero inference).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Row:
    forms: tuple[str, ...]
    codes: tuple[str, ...]
    labels: tuple[str, ...]


ROWS = {
    "revenue": Row(("PL",), ("FL",), (r"chiffres? d.affaires? nets?", r"montant net du chiffre")),
    "goods": Row(("PL",), ("FS",), (r"^achats de marchandises",)),
    "goods_change": Row(("PL",), ("FT",), (r"^variation.*stock.*marchandises",)),
    "materials": Row(("PL",), ("FU",), (r"^achats de matieres",)),
    "materials_change": Row(("PL",), ("FV",), (r"^variation.*stock.*mati[eè]res",)),
    "production_inventory": Row(("PL",), ("FM",), (r"^production stock",)),
    "wages": Row(("PL",), ("FY",), (r"^salaires et tra[i]?te",)),
    "social": Row(("PL",), ("FZ",), (r"^charges soc[i]?ales",)),
    "external": Row(("PL",), ("FW",), (r"^autres achats (?:et|&) charges externes",)),
    "depreciation": Row(
        ("PL",),
        ("GA",),
        (r"^.? ?dotations aux amortissements", r"^dotations.*amortissement.*immobilisation"),
    ),
    "financial": Row(("PL", "PL_CONT"), ("GV",), (r"^(?:2 ?- ?)?resultat finan",)),
    "tax": Row(("PL", "PL_CONT"), ("HK",), (r"^impots sur les benefices",)),
    "assets": Row(
        ("ASSETS",),
        ("CO",),
        (
            r"^total general",
            r"^total actif(?! immobil| circul)",
        ),
    ),
    "equity": Row(
        ("LIABILITIES",), ("DL",), (r"^total (?:des )?capitaux propres", r"^total \(?i\)?$")
    ),
    "capital": Row(("LIABILITIES",), ("DA",), (r"^capital social", r"^capital$")),
    "cash": Row(("ASSETS",), ("CF",), (r"^dispon\s?[i]?bilites",)),
    "vmp": Row(("ASSETS",), ("CD",), (r"^valeurs mobil.*placement",)),
    "workforce": Row(
        ("META",), ("YP",), (r"effectif moyen (?:du personnel|du personnal|des salaries)",)
    ),
    "liabilities": Row(
        ("LIABILITIES",),
        ("EE",),
        (
            r"^total general",
            r"^total passif",
        ),
    ),
}

FIELDS = {
    "PL_REVENUE_FRGAAP": ("revenue",),
    "PL_COGS_FRGAAP": (
        "goods",
        "goods_change",
        "materials",
        "materials_change",
        "production_inventory",
    ),
    "PL_PERSONNEL_COSTS_FRGAAP": ("wages", "social"),
    "PL_EXT_SERVICES_COSTS_FRGAAP": ("external",),
    "PL_DEPRECIATION_AMORTIZATION_FRGAAP": ("depreciation",),
    "PL_FINANCIAL_RESULTS_FRGAAP": ("financial",),
    "PL_INCOME_TAX_FRGAAP": ("tax",),
    "BS_TOTAL_ASSETS_FRGAAP": ("assets",),
    "BS_TOTAL_EQUITY_FRGAAP": ("equity",),
    "BS_CAPITAL_EQUITY_FRGAAP": ("capital",),
    "BS_CASH_CURRENT_ASSET_FRGAAP": ("cash",),
    "META_AVG_WORKFORCE_FRGAAP": ("workforce",),
}

INTERPRETATIONS = {
    "BS_CAPITAL_EQUITY_FRGAAP": "Called-up share capital (DA), following the explicit notes; reserves and premiums are not added despite the broader label.",
    "BS_CASH_CURRENT_ASSET_FRGAAP": "Disponibilites (CF), following the notes; VMP is disclosed separately when readable, without assuming all investments qualify as cash equivalents.",
    "PL_DEPRECIATION_AMORTIZATION_FRGAAP": "Depreciation/amortisation (GA), following the English label and notes; provisions are excluded despite the broader French label.",
    "PL_COGS_FRGAAP": "FS + FT + FU + FV + FM, the literal additive French label; signed production stockee is added, not silently negated. Omit if any component is unobserved. This is a challenge-specific measure, not a universal COGS definition.",
}
