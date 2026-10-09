# Luce Kernel

The column interpreter behind luced-3d's Code node: per-element code (Houdini's Wrangle)
written in Luce Base, run over millions of elements at once. It knows nothing about
meshes: a host hands it named, typed columns and gets named, typed columns back.

```prisma
def dependency "luce-kernel" {
    str owner = "dymokomi"
    str version = "^0.1.0"
}
```

Three public modules:

- `luce_kernel.engine`: the column IR, its `Builder`, `verify`, and `run`. A program is a
  flat list of instructions over typed registers (`f32 f64 i32 i64 u32 u64 mask`; a vector
  is 2 to 4 consecutive registers). `run` executes every instruction over a chunk of lanes
  (4096 by default) as one tight loop, chunks in parallel. A would-be Base trap (bounds,
  overflow, division by zero, failed conversion, `assert`, `trap`, a runaway loop) stops
  the run with a `Fault`: the source line and column and the lowest failing lane, the
  same at any thread count. The engine itself never traps.
- `luce_kernel.lib`: the functions a snippet calls without importing them, in Base
  spelling: `dot cross length length2 distance distance2 normalized`, `lerp clamp fit
  fit01 smooth degrees radians`, `rand rand3 rand64`, Perlin `noise`/`snoise` in 1 to 4
  dimensions (`noise1 noise2 noise noise4`), each with f64 forms (`64` suffix). VEX's
  math and transforms in VEX's row-vector convention: `Mat3`/`Mat4` (identity, rotation,
  transposed, inverted, determinant, multiply, transform, rotate/prerotate/scale/
  prescale/translate/pretranslate), `Quat` with `quaternion qmultiply qrotate qinvert
  qconvert slerp eulertoquaternion quaterniontoeuler`, `maketransform cracktransform
  lookat dihedral polardecomp` with the `xform_*` orders, `abs sign frac rint trunc min
  max avg sum product pow exp log log10 cbrt sinpi cospi tanpi`, `solvequadratic
  solvecubic`, the point distances, and `efit fit10 fit11 invlerp lspline cspline kspline
  spline`. The engine runs the first group as column operations; the rest lower from their
  Base bodies like a snippet's own helpers (structs, methods and all). A snippet imports
  only the lib names it uses and does not declare itself.

- `luce_kernel.lower`: from the user's snippet text to a program. `wrap` puts the body in
  the Run Over entry function (`point(p: Point*, k: const Kernel*)`, given by the host),
  `write_root` lays out the modules the checker resolves imports against, and `compile`
  checks the module with luce-base's own checker (`embed.Library`) and lowers the typed
  tree. A `Host` says what its API members are (column fields, accessors by literal name,
  the element number, uniforms and parameters, builtins). Element-dependent conditions
  become exec masks, uniform ones jumps; helpers in the header are inlined. Every
  diagnostic and fault maps back to the user's line and column.

```luce
from luce_kernel import lower
from luce_kernel.lower import Host, RunOver

var host = Host()
try host.field("Point", "P", "P", 3)          # p.P is the P column, 3 components
try host.element("Point", "ptnum")
try host.parameter("Kernel", "f32")            # k.f32("amount", 0.2): a spare parameter
try host.column("P", .f32, 3)                  # what the input holds
try lower.write_root(root)                     # then the host's own stubs under root
let points = RunOver(entry = "point", parameters = "p: Point*, k: const Kernel*",
                     imports = "from luce_geocore.code import Point, Kernel")
var compiled = try lower.compile(root, points, header, "p.P[1] += math32.sin(p.P[0] * 4.0) * 0.1", &host)
defer compiled.destroy()
for d in compiled.diagnostics(): show(d.part, d.line, d.column, d.message)
```

The IR can also be built by hand:

```luce
from luce_kernel import engine
from luce_kernel.engine import Builder, Column, Request

# p.P[1] += math32.sin(p.P[0] * 4.0) * 0.1, by hand
var b = Builder()
let x = b.input("P", 0, .f32)
let y = b.input("P", 1, .f32)
let wave = b.unary(.sin, b.binary(.mul, x, b.constant_f32(4.0)))
let moved = b.binary(.add, y, b.binary(.mul, wave, b.constant_f32(0.1)))
b.store(b.output("P", 1, .f32), moved)
var program = try b.finish()
defer program.destroy()
let request = Request(count = count, inputs = [Column.input_f32("P", positions, 3)],
                      outputs = [Column.output_f32("P", moved_positions, 3)], uniforms = no_uniforms)
if let fault = try engine.run(&program, &request):
    print(fault.describe(buffer, "point"))
```

The design is luced-3d's `docs/research/CODE-NODE.md`. The per-kind lane loops are
written by `tools/lanes.py` (run it after changing its tables), and the texts
`write_root` writes by `tools/sources.py` (run it after changing `src/lib`). Run `luc test` for the
unit, conformance, fault and fuzz suites; `python3 tests/bench/run.py` for timings.

Licensed under MIT or Apache-2.0, at your option.
