"""
EduSHIELD — Smart Auto-Ingestion
================================
Scans a folder (or accepts individual files) and ingests everything it finds.
Works with .pptx, .pdf, .docx, .txt — no hardcoding needed.

Usage:
------
# Ingest an entire folder, assigning all files to one course + module:
  python run_ingestion.py --folder slides/CSE1321 --course CSE1321 --module "M2 — Repetition & Loops"

# Ingest a single file:
  python run_ingestion.py --file slides/CSE1321/m2_p2-repetition.pptx --course CSE1321 --module "M2 — Repetition & Loops"

# Ingest a course folder that has sub-folders named after modules:
  python run_ingestion.py --folder slides/CSE1321 --course CSE1321 --auto-modules
  (folder structure: slides/CSE1321/M2_Loops/file.pptx -> module = "M2_Loops")

# Ingest everything under slides/ interactively (prompts for each sub-folder):
  python run_ingestion.py --folder slides --interactive

# Rebuild vector index only (no ingestion):
  python run_ingestion.py --rebuild-index
"""
import sys, os, argparse, glob
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "core"))

from core.educational_agent import SimpleEducationalAgent
from config import (NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD,
                    NEO4J_DATABASE, CHROMA_PATH, PARLEY_API_KEY,
                    COURSE_REGISTRY)

SUPPORTED = {".pptx", ".pdf", ".docx", ".txt"}


def get_agent():
    return SimpleEducationalAgent(
        neo4j_uri=NEO4J_URI, neo4j_user=NEO4J_USER,
        neo4j_password=NEO4J_PASSWORD, neo4j_database=NEO4J_DATABASE,
        chroma_path=CHROMA_PATH, parley_api_key=PARLEY_API_KEY,
    )


def ingest_file(agent, filepath, course_id, module_name):
    """Ingest one file. Returns counts dict."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext not in SUPPORTED:
        print(f"  ⏭  Skipping unsupported format: {os.path.basename(filepath)}")
        return {}
    print(f"    {os.path.basename(filepath)}")
    print(f"       course={course_id}  module={module_name}")
    try:
        counts = agent.ingest_material(
            filepath=filepath,
            course_id=course_id,
            module_name=module_name,
        )
        print(f"       [ok] +{counts.get('concepts',0)} concepts  "
              f"+{counts.get('facts',0)} facts  "
              f"+{counts.get('relationships',0)} rels")
        return counts
    except Exception as e:
        print(f"       [x] {e}")
        return {}


def scan_files(folder):
    """Return all supported files in a folder (non-recursive)."""
    files = []
    for ext in SUPPORTED:
        files.extend(glob.glob(os.path.join(folder, f"*{ext}")))
    return sorted(files)


def scan_files_recursive(folder):
    """Return all supported files recursively, preserving sub-folder structure."""
    files = []
    for root, dirs, filenames in os.walk(folder):
        dirs.sort()
        for fn in sorted(filenames):
            if os.path.splitext(fn)[1].lower() in SUPPORTED:
                files.append(os.path.join(root, fn))
    return files


def merge_counts(total, counts):
    for k in ("concepts", "facts", "relationships", "examples"):
        total[k] = total.get(k, 0) + counts.get(k, 0)


def print_summary(total, errors):
    print("\
" + "=" * 60)
    print(f"TOTAL: {total.get('concepts',0)} concepts · "
          f"{total.get('facts',0)} facts · "
          f"{total.get('relationships',0)} relationships · "
          f"{total.get('examples',0)} examples")
    if errors:
        print(f"\
⚠️  {len(errors)} file(s) failed:")
        for e in errors: print(f"  {e}")
    else:
        print("[ok] All files ingested successfully")


# -- Modes -----------------------------------------------------------------

def mode_single_file(args):
    """--file PATH --course X --module Y"""
    agent = get_agent()
    total, errors = {}, []
    c = ingest_file(agent, args.file, args.course, args.module)
    if c:
        merge_counts(total, c)
    else:
        errors.append(args.file)
    print_summary(total, errors)
    print("\
Rebuilding vector index...")
    n = agent.rag.build_index()
    print(f"[ok] Vector index: {n} vectors")
    agent.close()


def mode_folder_flat(args):
    """--folder PATH --course X --module Y  (all files -> same course+module)"""
    files = scan_files(args.folder)
    if not files:
        print(f"No supported files found in {args.folder}")
        return
    print(f"Found {len(files)} file(s) in {args.folder}")
    agent = get_agent()
    total, errors = {}, []
    for fp in files:
        c = ingest_file(agent, fp, args.course, args.module)
        if c: merge_counts(total, c)
        else: errors.append(fp)
    print_summary(total, errors)
    print("\
Rebuilding vector index...")
    n = agent.rag.build_index()
    print(f"[ok] Vector index: {n} vectors")
    agent.close()


def mode_auto_modules(args):
    """
    --folder slides/CSE1321 --course CSE1321 --auto-modules
    Sub-folder name becomes the module_name.
    If files are at the top level (not in sub-folders), they get module_name = course_id.
    """
    agent = get_agent()
    total, errors = {}, []

    # Top-level files -> module = course_id
    top_files = scan_files(args.folder)
    if top_files:
        print(f"\
[{args.course}] Top-level files -> module: {args.course}")
        for fp in top_files:
            c = ingest_file(agent, fp, args.course, args.course)
            if c: merge_counts(total, c)
            else: errors.append(fp)

    # Sub-folder files -> module = sub-folder name
    for entry in sorted(os.scandir(args.folder), key=lambda e: e.name):
        if not entry.is_dir():
            continue
        module_name = entry.name  # folder name IS the module name
        sub_files   = scan_files(entry.path)
        if not sub_files:
            continue
        print(f"\
[{args.course}] Module: {module_name}  ({len(sub_files)} files)")
        for fp in sub_files:
            c = ingest_file(agent, fp, args.course, module_name)
            if c: merge_counts(total, c)
            else: errors.append(fp)

    print_summary(total, errors)
    print("\
Rebuilding vector index...")
    n = agent.rag.build_index()
    print(f"[ok] Vector index: {n} vectors")
    agent.close()


def mode_interactive(args):
    """
    --folder slides --interactive
    Scans sub-folders, prompts user to assign each to a course + module.
    Unknown courses can be typed in freely.
    """
    print("\
Known courses:")
    for cid, c in COURSE_REGISTRY.items():
        print(f"  {cid} — {c['name']}")
    print()

    agent = get_agent()
    total, errors = {}, []

    entries = sorted([e for e in os.scandir(args.folder) if e.is_dir()],
                     key=lambda e: e.name)

    # Also check for files directly in root
    root_files = scan_files(args.folder)
    if root_files:
        entries_files = [(args.folder, root_files, "root")]
    else:
        entries_files = []

    for entry in entries:
        sub_files = scan_files_recursive(entry.path)
        if not sub_files:
            continue
        entries_files.append((entry.path, sub_files, entry.name))

    for folder_path, files, label in entries_files:
        print(f"\
 Folder: {label}  ({len(files)} files)")
        for f in files[:5]:
            print(f"   {os.path.basename(f)}")
        if len(files) > 5:
            print(f"   ... and {len(files)-5} more")

        course_id   = input(f"  Course ID (e.g. CSE1321): ").strip()
        module_name = input(f"  Module name (e.g. M2 — Repetition & Loops): ").strip()

        if not course_id or not module_name:
            print("  ⏭  Skipped (no input)")
            continue

        for fp in files:
            c = ingest_file(agent, fp, course_id, module_name)
            if c: merge_counts(total, c)
            else: errors.append(fp)

    print_summary(total, errors)
    print("\
Rebuilding vector index...")
    n = agent.rag.build_index()
    print(f"[ok] Vector index: {n} vectors")
    agent.close()


def mode_rebuild_index(args):
    """
    FIX (BUG 12): args was referenced but not passed (was _args).
    Writes DomainConfig for all known courses then rebuilds the index.
    """
    agent = get_agent()
    print("Writing domain config to KG...")
    if args.course:
        _write_domain_config(agent, args.course)
    else:
        # Write for all courses in registry if no specific course given
        for cid in COURSE_REGISTRY:
            _write_domain_config(agent, cid)
    print("\nRebuilding vector index...")
    n = agent.rag.build_index()
    print(f"[ok] Done: {n} vectors")
    agent.close()


# -- CLI -------------------------------------------------------------------

def _write_domain_config(agent, course_id: str):
    """
    Build and store DomainConfig in Neo4j for ANY course.

    FIX (BUG 13): Now also stores modules list in Neo4j so app never needs
    COURSE_REGISTRY for modules at runtime. Modules are read from ingested
    Concept.module_name values (set by --auto-modules), with seed fallback.

    FIX (BUG 14): boundary_terms now correctly read from COURSE_REGISTRY
    entry's boundary_terms key (which was added in the updated config.py).
    Old config had no boundary_terms key -> always got empty list [].

    Works for unknown courses too (empty seed dict -> auto-builds from KG).
    """
    import re
    from config import COURSE_REGISTRY, COURSE_REGISTRY as CR

    # Seed data — empty dict for brand-new courses not in COURSE_REGISTRY
    course  = COURSE_REGISTRY.get(course_id, {})
    prereqs = course.get("prerequisites", [])

    # ── 1. Modules from KG (authoritative after --auto-modules ingestion) ──
    kg_modules = []
    try:
        with agent.kg._session() as s:
            result = s.run(
                "MATCH (c:Concept) WHERE c.course_id = $cid AND c.module_name IS NOT NULL "
                "RETURN DISTINCT c.module_name AS mod ORDER BY mod",
                cid=course_id
            )
            kg_modules = [r["mod"] for r in result if r.get("mod")]
    except Exception:
        pass
    # Fall back to seed modules if KG has none yet
    modules = kg_modules if kg_modules else course.get("modules", [])

    # ── 2. Module-name keywords (from actual modules) ─────────────────────
    module_words = set()
    for m in modules:
        clean = re.sub(r'^M\d+\s*[-—]\s*', '', m)
        for w in clean.lower().split():
            if len(w) > 3 and w not in {"with", "and", "for", "the", "review"}:
                module_words.add(w)

    # ── 3. in_domain_extras from seed (empty for unknown courses) ─────────
    extras = set(course.get("in_domain_extras", []))

    # ── 4. Clean concept labels from KG ───────────────────────────────────
    concept_words = set()
    _JUNK = re.compile(
        r'^(slide\s*\d+|para\s*\d+|chapter\s*\d+|our\s|some\s|more\s|'
        r'the\s|this\s|introduction|overview|summary|agenda|midterm)',
        re.IGNORECASE
    )
    try:
        with agent.kg._session() as s:
            result = s.run(
                "MATCH (c:Concept) WHERE c.course_id = $cid RETURN c.label AS label",
                cid=course_id
            )
            for r in result:
                label = r["label"] or ""
                if label and not _JUNK.match(label) and len(label) < 60:
                    for w in label.lower().split():
                        if len(w) > 3 and w not in {"with", "and", "for", "the"}:
                            concept_words.add(w)
    except Exception:
        pass

    in_domain_keywords = list(
        set([course_id.lower()]) | module_words | extras | concept_words
    )

    # FIX (BUG 14): boundary_terms from registry entry (now has this key)
    # Empty list for unknown courses — add to COURSE_REGISTRY when desired
    boundary_terms = course.get("boundary_terms", [])

    # excluded_terms: all known courses that are not prereqs
    all_known = set(CR.keys())
    try:
        with agent.kg._session() as s:
            rows = s.run("MATCH (d:DomainConfig) RETURN d.course_id AS cid")
            for r in rows:
                if r.get("cid"):
                    all_known.add(r["cid"])
    except Exception:
        pass
    excluded_terms = [
        cid.lower() for cid in all_known
        if cid != course_id and cid not in prereqs
    ]

    config = {
        "domain_name":          course_id,
        "course_name":          course.get("name", course_id),
        "in_domain_keywords":   in_domain_keywords,
        "boundary_terms":       boundary_terms,
        "excluded_terms":       excluded_terms,
        "prerequisite_courses": prereqs,
        "modules":              modules,       # FIX (BUG 13): stored in Neo4j
    }
    agent.kg.write_domain_config(config)
    in_registry = course_id in COURSE_REGISTRY
    print(f"[ok] DomainConfig written for {course_id} "
          f"({'registered' if in_registry else 'NEW — auto-configured'}):")
    print(f"     modules={len(modules)}  in_domain_kw={len(in_domain_keywords)}  "
          f"boundary_terms={len(boundary_terms)} "
          f"({'from registry' if boundary_terms else 'none — add to COURSE_REGISTRY'})")


def main():
    p = argparse.ArgumentParser(
        description="EduSHIELD Smart Ingestion — ingest any .pptx/.pdf/.docx/.txt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    p.add_argument("--file",          help="Path to a single file")
    p.add_argument("--folder",        help="Path to a folder of files")
    p.add_argument("--course",        help="Course ID (e.g. CSE1321)")
    p.add_argument("--module",        help="Module name (e.g. 'M2 — Repetition & Loops')")
    p.add_argument("--auto-modules",  action="store_true",
                   help="Use sub-folder names as module names")
    p.add_argument("--interactive",   action="store_true",
                   help="Prompt for course/module per sub-folder")
    p.add_argument("--rebuild-index", action="store_true",
                   help="Rebuild ChromaDB vector index without re-ingesting")
    args = p.parse_args()

    if args.rebuild_index:
        mode_rebuild_index(args)
    elif args.file:
        if not args.course or not args.module:
            p.error("--file requires --course and --module")
        mode_single_file(args)
    elif args.folder and args.auto_modules:
        if not args.course:
            p.error("--auto-modules requires --course")
        mode_auto_modules(args)
    elif args.folder and args.interactive:
        mode_interactive(args)
    elif args.folder:
        if not args.course or not args.module:
            p.error("--folder requires --course and --module (or --auto-modules or --interactive)")
        mode_folder_flat(args)
    else:
        p.print_help()


if __name__ == "__main__":
    main()