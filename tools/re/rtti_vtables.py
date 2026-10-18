#!/usr/bin/env python3
"""Recover MSVC x86 RTTI class names and vtables from a local executable.

TypeDescriptor = {type_info vtable, spare, ".?AV<name>@@"}; a
CompleteObjectLocator (signature 0) points at a TypeDescriptor at +12, and
vtable[-1] points at the locator. Output TSV: vtable VA, slot count, locator
offset (non-zero for secondary bases), demangled class name, and one
slot,function VA list. Requires pefile.
"""
import argparse
import re
import struct

import pefile


def demangle(raw):
    # ".?AVCUnit@@" -> "CUnit"; ".?AVCLrPath@NIpse@@" -> "NIpse::CLrPath"
    body = raw[4:-2] if raw.endswith("@@") else raw[4:]
    if body.startswith("?$"):
        return raw  # templates: keep mangled, unambiguous
    return "::".join(reversed([p for p in body.split("@") if p]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("exe")
    args = ap.parse_args()
    pe = pefile.PE(args.exe, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    data = pe.__data__
    text = next(s for s in pe.sections if s.Name.startswith(b".text"))
    text_lo, text_hi = base + text.VirtualAddress, base + text.VirtualAddress + text.Misc_VirtualSize

    def va(off):
        return base + pe.get_rva_from_offset(off)

    names = {}
    for m in re.finditer(rb"\.\?A[VU][^\0]{1,240}@@\0", data):
        names[va(m.start()) - 8] = m.group()[:-1].decode("latin-1")

    rdata = [s for s in pe.sections if s.Name.rstrip(b"\0") in (b".rdata", b".data")]
    locators = {}
    for s in rdata:
        blob = data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        for o in range(0, len(blob) - 20, 4):
            sig, off, cd, td, hier = struct.unpack_from("<5I", blob, o)
            if sig == 0 and td in names and off < 0x10000:
                locators[base + s.VirtualAddress + o] = (td, off)

    print("vtable\tslots\toffset\tclass\tfunctions")
    for s in rdata:
        blob = data[s.PointerToRawData:s.PointerToRawData + s.SizeOfRawData]
        for o in range(0, len(blob) - 8, 4):
            col = struct.unpack_from("<I", blob, o)[0]
            if col not in locators:
                continue
            vt = base + s.VirtualAddress + o + 4
            fns = []
            p = o + 4
            while p + 4 <= len(blob):
                f = struct.unpack_from("<I", blob, p)[0]
                if not (text_lo <= f < text_hi):
                    break
                fns.append(f)
                p += 4
                # The next vtable's locator pointer ends this one.
                if p + 4 <= len(blob) and struct.unpack_from("<I", blob, p)[0] in locators:
                    break
            td, off = locators[col]
            print(f"0x{vt:08X}\t{len(fns)}\t{off}\t{demangle(names[td])}\t"
                  + ",".join(f"0x{f:08X}" for f in fns))


if __name__ == "__main__":
    main()
