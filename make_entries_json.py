# make_entries_json.py
import csv, json, re
from pathlib import Path

# === CONFIGURE THESE VALUES ===
CSV_PATH    = Path('/Users/aplab/Desktop/000 - Boltz-2 individual/input UniProt ID test.csv')
DATA_PARENT = Path('/Users/aplab/Desktop/000 - Boltz-2 individual/GitHub Test Dataset/uniprot-data/UniProt-Dataset')
GH_USER     = 'BM-DB'
DATA_REPO   = "uniprot-data"
DATA_BRANCH = "main"   # usually "main"
OUTPUT_JSON = Path('/Users/aplab/Desktop/000 - Boltz-2 individual/GitHub Test Browser/uniprot-browser/data/entries.json')
# ==============================

RAW_BASE = f"https://raw.githubusercontent.com/{GH_USER}/{DATA_REPO}/{DATA_BRANCH}"

def normalize_header(s: str) -> str:
    # strip, collapse spaces, replace NBSP, lower
    s = (s or "").replace("\u00A0", " ")   # NBSP -> space
    s = " ".join(s.strip().split())
    return s.lower()

def sniff_dialect(sample_bytes: bytes):
    try:
        # csv.Sniffer works on str, so decode first (keep errors='ignore' just for sniffing)
        sample_text = sample_bytes.decode("utf-8", errors="ignore")
        return csv.Sniffer().sniff(sample_text, delimiters=[",",";","\t","|"])
    except Exception:
        # fallback to comma
        d = csv.excel()
        d.delimiter = ","
        return d

def open_csv_reader(path: Path):
    # Read a sample to sniff delimiter
    with path.open("rb") as fb:
        sample = fb.read(4096)
    dialect = sniff_dialect(sample)

    # Now open text with BOM handling; newline='' lets csv handle newlines correctly
    f = path.open("r", encoding="utf-8-sig", newline="")
    reader = csv.DictReader(f, dialect=dialect)
    return f, reader

def locate_uid_field(fieldnames):
    norm_map = {normalize_header(h): h for h in fieldnames if h is not None}
    # Accept common variants
    candidates = [
        "uniprot id",        # expected
        "uniprot_id",        # underscore variant
        "uniprot accession", # just in case
        "id",                # last-ditch
    ]
    for key in candidates:
        if key in norm_map:
            return norm_map[key]
    return None

def find_files_for(uid: str):
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
                if re.search(rf"monomer_Boltz-2_{re.escape(uid)}", f.name):
                    cif_path = f
                    break

    # FASTA: exactly <UID>.fasta under seq_dir
    if seq_dir.is_dir():
        cand = seq_dir / f"{uid}.fasta"
        if cand.is_file():
            fasta_path = cand

    if not (cif_path and fasta_path):
        return None, None

    return (
        cif_path.relative_to(DATA_PARENT).as_posix(),
        fasta_path.relative_to(DATA_PARENT).as_posix(),
    )

def main():
    entries, missing = [], []

    f, reader = open_csv_reader(CSV_PATH)
    with f:
        uid_field = locate_uid_field(reader.fieldnames or [])
        if not uid_field:
            # Helpful debug print so you can see what Python actually sees
            print("DEBUG fieldnames seen by csv module:", reader.fieldnames)
            raise AssertionError("Could not find a 'UniProt ID' column (case/space-insensitive).")

        for row in reader:
            raw_val = row.get(uid_field, "")
            uid = str(raw_val).strip()
            if not uid:
                continue  # skip empty rows

            cif_rel, fasta_rel = find_files_for(uid)
            if not (cif_rel and fasta_rel):
                missing.append(uid)
                continue

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