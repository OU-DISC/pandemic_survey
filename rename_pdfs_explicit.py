"""Explicit renames for near-miss PDF filenames to BibTeX ids."""
import re
import codecs
from pathlib import Path
from update_data import update

PDF = Path("src/data/papers_pdf")
ids = set(
    re.findall(
        r"@\w+\s*\{\s*([^,\s]+)",
        codecs.open("bib/references.bib", "r", "utf-8-sig").read(),
    )
)

MAP = {
    "asymptomatics2023mcneill": "mcneill_asymptomatics_2023",
    "attention2022kanwal": "kanwal_attention-based_2022",
    "cangjie2021zhang": "zhang_cangjies_2021",
    "cone2022bovo": "bovo_cone_2022",
    "covidexplorer2020ambavi": "ambavi_covidexplorer_2020",
    "covidvis2023papageorgiadis": "papageorgiadis_covid-vis_2022",
    "cvas2022yang": "yang_cvas_2022",
    "dualstage2024tsai": "tsai_dualstage_2024",
    "han2024cybergis": "han_cybergis-vis_2024",
    "hao2023does": "hao_does_2023",
    "interactive2022humayoun": "humayoun_interactive_2022",
    "mapping2021zhang": "zhang2021mapping",
    "sarkar2023adhoc": "sarkar_ad-hoc_2023",
    "providing2020gaie": "gaie_providing_2021",
    "soap2020mcghee": "mcghee_soap_2019",
    "leveraging2020li": "latif_leveraging_2020",
    "analysis2021kamaludin": "kharismawati_kamaludin_analysis_2021",
    "covid2020hussain": "hussain_covid-19_2020",
    "covid2022collins": "collins_covid_2022",
    "covid2020biswas": "biswas_covid-19_2020",
    "min2021crowdmap": "min_crowdmap_2021",
    "multivariate2022hartanto": "hartanto_multivariate_2022",
    "will2020albert": "albert_will_2020",
    "web2021maclean": "maclean_web-based_2021",
    "text2022singla": "singla_text_2022",
    "towards2015krekhov": "krekhov_towards_2015",
    "Data_Visualization_Tool_for_Covid-19_and_Crime_Data": "keswani_data_2022",
    "integration2014kostkova": "kostkova2014integration",
}

renamed = 0
skipped = []
for stem, bib_id in MAP.items():
    src = PDF / f"{stem}.pdf"
    if not src.exists():
        skipped.append((stem, "source missing"))
        continue
    if bib_id not in ids:
        close = [i for i in ids if bib_id.split("_")[0].lower() in i.lower()]
        skipped.append((stem, f"id missing: {bib_id}; close={close[:3]}"))
        continue
    dst = PDF / f"{bib_id.replace(':', '_')}.pdf"
    if dst.exists() and dst.resolve() != src.resolve():
        skipped.append((stem, f"target exists: {dst.name}"))
        continue
    print(f"{src.name} -> {dst.name}")
    src.rename(dst)
    renamed += 1

print("renamed", renamed)
print("skipped:")
for s in skipped:
    print(" ", s)

update()
pdfs = list(PDF.glob("*.pdf"))
matched = sum(
    1
    for p in pdfs
    if p.stem in ids or any(i.replace(":", "_") == p.stem for i in ids)
)
print(f"Total {len(pdfs)} matching {matched} non-matching {len(pdfs) - matched}")
non = [
    p.name
    for p in pdfs
    if p.stem not in ids and not any(i.replace(":", "_") == p.stem for i in ids)
]
print("Remaining non-matching:")
for n in non:
    print(" ", n)
