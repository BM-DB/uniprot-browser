# make_entries_json.py  — Option B (repo-root aware, robust CSV)
import csv, json, re
from pathlib import Path

# === CONFIGURE THESE VALUES (pre-filled from your setup) ===
CSV_PATH    = Path('/Users/aplab/Desktop/000 - Boltz-2 individual/input UniProt ID test.csv')
REPO_ROOT   = Path('/Users/aplab/Desktop/000 - Boltz-2 individual/GitHub Test Dataset/uniprot-data')  # repo root
DATA_PARENT = REPO_ROOT / 'UniProt-Dataset'  # ID folders live under this subfolder

GH_USER     = 'BM-DB'
DATA_REPO   = 'uniprot-data'
DATA_BRANCH = 'main'   # branch name on GitHub
OUTPUT_JSON = Path('/Users/aplab/Desktop/000 - Boltz-2 individual/GitHub Test Browser/uniprot-browser/data/entries.json')
# ===========================================================

RAW_BASE = f"https://raw.githubusercontent.com/{GH_USER}/{DATA_REPO}/{DATA_BRANCH}"

def normalize_header(s: str) -> str:
    # strip, collapse spaces, replace NBSP, lower
    s = (s or "").replace("\u00A0", " ")
    s = " ".join(s.strip().split())
    return s.lower()

def sniff_dialect(sample_bytes: bytes):
    try:
        sample_text = sample_bytes.decode("utf-8", errors="ignore")
        return csv.Sniffer().sniff(sample_text, delimiters=[",", ";", "\t", "|"])
    except Exception:
        d = csv.excel()
        d.delimiter = ","
        return d

def open_csv_reader(path: Path):
    # sniff delimiter using a small sample
    with path.open("rb") as fb:
        sample = fb.read(4096)
    dialect = sniff_dialect(sample)
    # open text with BOM handling
    f = path.open("r", encoding="utf-8-sig", newline="")
    reader = csv.DictReader(f, dialect=dialect)
    return f, reader

def locate_uid_field(fieldnames):
    norm_map = {normalize_header(h): h for h in fieldnames if h is not None}
    for key in ("uniprot id", "uniprot_id", "uniprot accession", "id"):
        if key in norm_map:
            return norm_map[key]
    return None

def find_files_for(uid: str):
    """Return repo-root-relative paths (as POSIX strings) for CIF and FASTA, or (None, None)."""
    id_root = DATA_PARENT / uid
    if not id_root.is_dir():
        return None, None

    boltz_dir = id_root / f"{uid}_Boltz-2"
    seq_dir   = id_root / f"{uid}_Sequence"

    cif_path = None
    fasta_path = None

    # CIF: monomer_Boltz-2_<UID>.cif/.mmcif anywhere under boltz_dir
    if boltz_dir.is_dir():
        for f in boltz_dir.rglob("*"):
            if f.is_file() and f.suffix.lower() in (".cif", ".mmcif"):
                if re.search(rf"^monomer_Boltz-2_{re.escape(uid)}(\.|_|-)", f.name) or f.name == f"monomer_Boltz-2_{uid}.cif" or f.name == f"monomer_Boltz-2_{uid}.mmcif":
                    cif_path = f
                    break
        if cif_path is None:
            # fallback: any cif/mmcif containing the uid
            for f in boltz_dir.rglob("*"):
                if f.is_file() and f.suffix.lower() in (".cif", ".mmcif"):
                    if uid in f.name:
                        cif_path = f
                        break

    # FASTA: exactly <UID>.fasta under seq_dir
    if seq_dir.is_dir():
        cand = seq_dir / f"{uid}.fasta"
        if cand.is_file():
            fasta_path = cand

    if not (cif_path and fasta_path):
        return None, None

    # Return paths relative to the REPO_ROOT (matches GitHub tree)
    return (
        cif_path.relative_to(REPO_ROOT).as_posix(),
        fasta_path.relative_to(REPO_ROOT).as_posix(),
    )

def main():
    entries, missing = [], []

    f, reader = open_csv_reader(CSV_PATH)
    with f:
        uid_field = locate_uid_field(reader.fieldnames or [])
        if not uid_field:
            print("DEBUG fieldnames seen by csv module:", reader.fieldnames)
            raise AssertionError("Could not find a 'UniProt ID' column (case/space-insensitive).")

        for row in reader:
            uid = str(row.get(uid_field, "")).strip()
            if not uid:
                continue  # skip blank rows

            paths = find_files_for(uid)
            if not paths:
                missing.append(uid)
                continue
            cif_rel, fasta_rel = paths

            entries.append({
                "uniprot_id": uid,  # keep EXACT string (e.g., P05067 vs P05067-4)
                "files": {
                    "structure_cif": f"{RAW_BASE}/{cif_rel}",
                    "sequence_fasta": f"{RAW_BASE}/{fasta_rel}",
                }
            })

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps({"count": len(entries), "entries": entries}, indent=2))

    print(f"Wrote {len(entries)} entries → {OUTPUT_JSON}")
    if missing:
        print(f"{len(missing)} IDs missing files (first 15): {missing[:15]}")

if __name__ == "__main__":
    main()
