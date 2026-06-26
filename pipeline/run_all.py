"""run_all — orchestrate the full ProvBench pipeline (s1 -> s7, optionally s8/s9).

    python pipeline/run_all.py                 # extract..metadata (no DB/HF)
    python pipeline/run_all.py --load          # also load Supabase (needs SUPABASE_DB_URL)
    python pipeline/run_all.py --load --publish # also publish to HuggingFace (needs HF_TOKEN)
    python pipeline/run_all.py --force-extract  # re-hit the source APIs
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import utils  # noqa: E402

log = utils.get_logger("run_all")


def main() -> None:
    force = "--force-extract" in sys.argv
    do_load = "--load" in sys.argv
    do_publish = "--publish" in sys.argv

    import s1_extract_chembl
    import s2_extract_bindingdb
    import s3_standardize
    import s4_harmonize
    import s5_flag
    import s6_qc_report
    import s7_emit_metadata

    t0 = time.time()
    steps = [
        ("s1 extract ChEMBL", lambda: s1_extract_chembl.main(force=force)),
        ("s2 extract BindingDB", lambda: s2_extract_bindingdb.main(force=force)),
        ("s3 standardize", s3_standardize.main),
        ("s4 harmonize/consensus", s4_harmonize.main),
        ("s5 flag", s5_flag.main),
        ("s6 QC report", s6_qc_report.main),
        ("s7 emit metadata", s7_emit_metadata.main),
    ]
    if do_load:
        import s8_load_supabase
        steps.append(("s8 load Supabase", s8_load_supabase.main))
    if do_publish:
        import s9_publish_hf
        steps.append(("s9 publish HuggingFace", s9_publish_hf.main))

    for name, fn in steps:
        log.info("=" * 60)
        log.info(">>> %s", name)
        log.info("=" * 60)
        fn()

    log.info("Pipeline complete in %.1fs", time.time() - t0)


if __name__ == "__main__":
    main()
