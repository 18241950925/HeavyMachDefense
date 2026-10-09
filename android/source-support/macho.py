"""Read the ARM Mach-O metadata needed for small compatibility patches."""
import struct
from pathlib import Path


class MachO:
    def __init__(self, data):
        self.data = data
        self.segments = []
        self.sections = {}
        off = 28
        for _ in range(struct.unpack_from("<I", data, 16)[0]):
            cmd, size = struct.unpack_from("<II", data, off)
            if cmd == 1:
                vm, vs, fo, fs = struct.unpack_from("<4I", data, off + 24)
                self.segments.append((vm, vs, fo, fs))
                ns = struct.unpack_from("<I", data, off + 48)[0]
                for j in range(ns):
                    s = off + 56 + 68 * j
                    name = data[s:s + 16].split(b"\0")[0].decode()
                    addr, length, fileoff = struct.unpack_from("<3I", data, s + 32)
                    self.sections[name] = (addr, length, fileoff)
            off += size

    def offset(self, addr):
        for vm, vs, fo, fs in self.segments:
            if vm <= addr < vm + fs:
                return fo + addr - vm
        raise ValueError("Address outside file: " + hex(addr))

    def u32(self, addr):
        return struct.unpack_from("<I", self.data, self.offset(addr))[0]

    def string(self, addr):
        off = self.offset(addr)
        return self.data[off:self.data.index(b"\0", off)].decode("utf-8", "replace")

    def classes(self):
        addr, size, _ = self.sections["__objc_classlist"]
        for i in range(size // 4):
            cls = self.u32(addr + i * 4)
            ro = self.u32(cls + 16) & ~3
            name = self.string(self.u32(ro + 16))
            yield name, cls, ro

    def methods(self):
        for name, cls, ro in self.classes():
            for prefix, base in (("-", ro), ("+", self.u32(self.u32(cls) + 16) & ~3)):
                methods = self.u32(base + 20)
                if not methods:
                    continue
                stride = self.u32(methods) & 0xFFFF
                count = self.u32(methods + 4)
                for j in range(count):
                    m = methods + 8 + j * stride
                    selector = self.string(self.u32(m))
                    imp = self.u32(m + 8)
                    yield name, prefix, selector, imp


if __name__ == "__main__":
    import json
    root = Path(__file__).resolve().parents[1]
    m = MachO((root / "original/Payload/MachDefense.app/MachDefense").read_bytes())
    methods = list(m.methods())
    (root / "reference/methods.json").write_text(json.dumps(methods, indent=2))
    for cls, prefix, selector, imp in methods:
        if cls in ("DefaultAppDelegate", "QTable", "GuiBanner", "DataFile"):
            print(f"{hex(imp)} {prefix}[{cls} {selector}]")
