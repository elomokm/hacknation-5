"""Quick smoke test — run with: python test_extractor.py"""
from dotenv import load_dotenv
load_dotenv()

from extractor import extract_skills

TEXT = (
    "Je répare des téléphones depuis 3 ans dans mon quartier à Cotonou. "
    "Je change les écrans, les batteries, je soude des composants. "
    "Je gère aussi mes commandes de pièces sur WhatsApp."
)

skills = extract_skills(TEXT)
assert len(skills) > 0, "No skills extracted"
for s in skills:
    print(f"  [{s.category}] {s.name}  level={s.level}  conf={s.confidence:.2f}")

print(f"\nOK — {len(skills)} skills extracted")
