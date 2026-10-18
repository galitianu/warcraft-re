#!/usr/bin/env python3
"""Name JASS native implementations in an analyzed local Ghidra project.

Input is the TSV from jass_natives.py. Each implementation becomes
`jass_<Name>` with its JASS signature as a plate comment. Existing user names
are kept unless --force is given. Requires pyghidra and GHIDRA_INSTALL_DIR.
"""
import argparse
import csv
import os


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tsv")
    ap.add_argument("--project-dir", required=True)
    ap.add_argument("--project-name", required=True)
    ap.add_argument("--program", default="/war3-1.29.2-9231.exe",
                    help="program path inside the project")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    import pyghidra
    pyghidra.start()
    from ghidra.program.model.symbol import SourceType
    from ghidra.program.model.listing import CodeUnit
    from ghidra.app.cmd.function import CreateFunctionCmd

    rows = list(csv.DictReader(open(args.tsv), delimiter="\t"))
    project_dir = os.path.abspath(args.project_dir)
    with pyghidra.open_project(project_dir, args.project_name) as project, \
            pyghidra.program_context(project, args.program) as program:
        if program.getFunctionManager().getFunctionCount() == 0:
            raise SystemExit("program has no functions; run auto-analysis first")
        fm = program.getFunctionManager()
        space = program.getAddressFactory().getDefaultAddressSpace()
        renamed = created = kept = 0
        tx = program.startTransaction("apply JASS native names")
        try:
            for r in rows:
                addr = space.getAddress(int(r["impl_va"], 16))
                fn = fm.getFunctionAt(addr)
                if fn is None:
                    CreateFunctionCmd(addr).applyTo(program)
                    fn = fm.getFunctionAt(addr)
                    created += 1
                if fn is None:
                    print("cannot create function at", r["impl_va"], r["name"])
                    continue
                new = "jass_" + r["name"]
                user_named = fn.getSymbol().getSource() == SourceType.USER_DEFINED
                if user_named and not args.force and fn.getName() != new:
                    kept += 1
                    continue
                fn.setName(new, SourceType.ANALYSIS)
                fn.setComment(f"JASS native {r['name']} {r['signature']}\n"
                              f"registered at {r['registered_at']}")
                renamed += 1
        finally:
            program.endTransaction(tx, True)
        program.save("apply JASS native names", pyghidra.task_monitor())
        print(f"renamed={renamed} created={created} kept_user_names={kept}")


if __name__ == "__main__":
    main()
