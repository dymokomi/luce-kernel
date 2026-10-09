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

Two public modules:

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
  dimensions (`noise1 noise2 noise noise4`), each with f64 forms (`64` suffix).

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

The lowering from a checked Base snippet to this IR comes with the Base front end as a
library; see luced-3d's `docs/research/CODE-NODE.md`. The per-kind lane loops are
written by `tools/lanes.py` (run it after changing its tables). Run `luc test` for the
unit, conformance, fault and fuzz suites; `python3 tests/bench/run.py` for timings.

Licensed under MIT or Apache-2.0, at your option.
