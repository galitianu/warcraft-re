#!/usr/bin/env python3
"""Extract the JASS native registration table from a local WC3 executable.

Natives are registered by `push sig; push name; push impl; call REGISTER`.
The register target is located from a known native name, then every call to it
is decoded. Output is TSV: impl_va, name, signature, registration call site.
Reads only a local binary; writes no game data into the repository.

Requires: pefile, capstone (install outside the repo).
"""
import argparse
import collections
import sys

import capstone
import pefile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    ap.add_argument("--anchor", default="IssuePointOrder")
    ap.add_argument("--common-j", help="verify names against this common.j")
    args = ap.parse_args()

    pe = pefile.PE(args.exe, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    data = pe.__data__
    text = next(s for s in pe.sections if s.Name.startswith(b".text"))
    text_va = base + text.VirtualAddress
    code = data[text.PointerToRawData:text.PointerToRawData + text.SizeOfRawData]

    def cstr(va):
        try:
            o = pe.get_offset_from_rva(va - base)
        except pefile.PEFormatError:
            return None
        end = data.find(b"\0", o)
        if end < 0 or end - o > 256:
            return None
        try:
            return data[o:end].decode("ascii")
        except UnicodeDecodeError:
            return None

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.skipdata = True

    # Locate the registration function from the anchor's first push site.
    anchor_off = data.find(b"\0" + args.anchor.encode() + b"\0") + 1
    anchor_va = base + pe.get_rva_from_offset(anchor_off)
    site = code.find(b"\x68" + anchor_va.to_bytes(4, "little"))
    if site < 0:
        sys.exit("anchor string is not pushed in .text")
    register = None
    for ins in md.disasm(code[site:site + 32], text_va + site):
        if ins.mnemonic == "call":
            register = int(ins.op_str, 16)
            break
    if register is None:
        sys.exit("no registration call after anchor")

    rows = []
    i = 0
    while True:
        i = code.find(b"\xe8", i)
        if i < 0:
            break
        rel = int.from_bytes(code[i + 1:i + 5], "little", signed=True)
        call_va = text_va + i
        if call_va + 5 + rel == register and i >= 15:
            pushes = []
            j = i - 5
            while len(pushes) < 3 and j >= 0 and code[j] == 0x68:
                pushes.append(int.from_bytes(code[j + 1:j + 5], "little"))
                j -= 5
            if len(pushes) == 3:
                impl, name, sig = pushes[0], cstr(pushes[1]), cstr(pushes[2])
                if name and sig and sig.startswith("("):
                    rows.append((impl, name, sig, call_va))
        i += 1

    # A table whose implementations are all one address is a stub registry.
    by_impl = collections.Counter(r[0] for r in rows)
    stubs = {impl for impl, n in by_impl.items() if n > 50}
    print(f"# register=0x{register:08X} rows={len(rows)} "
          f"stub_impls={','.join(f'0x{s:08X}' for s in sorted(stubs))}", file=sys.stderr)
    real = [r for r in rows if r[0] not in stubs]

    if args.common_j:
        declared = set()
        for line in open(args.common_j, encoding="latin-1"):
            parts = line.split()
            if len(parts) > 2 and parts[0] in ("native", "constant") and "native" in parts[:2]:
                declared.add(parts[parts.index("native") + 1])
        found = {r[1] for r in real}
        print(f"# common.j natives={len(declared)} found={len(found & declared)} "
              f"missing={len(declared - found)} extra={len(found - declared)}", file=sys.stderr)
        for n in sorted(declared - found):
            print(f"# missing {n}", file=sys.stderr)

    print("impl_va\tname\tsignature\tregistered_at")
    for impl, name, sig, call_va in sorted(real, key=lambda r: r[3]):
        print(f"0x{impl:08X}\t{name}\t{sig}\t0x{call_va:08X}")


if __name__ == "__main__":
    main()
