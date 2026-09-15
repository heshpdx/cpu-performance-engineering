#!/usr/bin/env python3
"""Trace an image into a flat-colour SVG, one traced layer per colour.

    uv run --with pillow python3 vectorise.py --src img.jpg --out banner.svg

The image is reduced to a small palette, each colour becomes a bilevel mask,
and potrace turns each mask into paths. With --alphamax 0 the paths keep
their corners, which suits a die photograph: it is rectilinear already, so
the trace follows the block boundaries rather than rounding them off.
"""
import argparse
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

PATH_D = re.compile(r'<path[^>]*\sd="([^"]+)"', re.S)


def trace(mask, alphamax, turdsize, opttolerance, unit):
    """Run potrace over one bilevel mask and return its path data."""
    with tempfile.TemporaryDirectory() as tmp:
        pbm, svg = Path(tmp) / "m.pbm", Path(tmp) / "m.svg"
        mask.save(pbm)
        subprocess.run(["potrace", str(pbm), "-s", "-o", str(svg),
                        "-a", str(alphamax), "-t", str(turdsize),
                        "-O", str(opttolerance), "-u", str(unit), "--flat"], check=True)
        return PATH_D.findall(svg.read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--crop", default="", help="fractional x0,y0,x1,y1; aspect forced to --aspect")
    ap.add_argument("--aspect", type=float, default=3000 / 1100)
    ap.add_argument("--colours", type=int, default=18)
    ap.add_argument("--width", type=int, default=0,
                    help="width attribute on the svg; the viewBox stays at the traced size, so this only "
                         "sets how large a page lays it out. 0 uses the traced size")
    ap.add_argument("--crisp", action="store_true",
                    help="turn anti-aliasing off; right at the traced size, wrong once it is scaled up")
    ap.add_argument("--dim", type=float, default=1.0,
                    help="scale the palette's brightness; below 1 takes the banner down without\n"
                         "touching its hues")
    ap.add_argument("--palette-sat", type=float, default=1.0,
                    help="saturation applied to the derived palette; a cluster's mean is always less saturated "
                         "than the pixels in it, and this puts that back")
    ap.add_argument("--shadow-gamma", type=float, default=1.0,
                    help="above 1, cluster the colours on a shadow-lifted copy so the dark end gets its share "
                         "of the palette; the palette is mapped back afterwards, so the colours stay true")
    ap.add_argument("--method", default="MAXCOVERAGE", choices=["MEDIANCUT", "MAXCOVERAGE", "FASTOCTREE"],
                    help="median cut averages a die's interleaved colours into mud; max coverage keeps them")
    ap.add_argument("--scale", type=float, default=1.0, help="resample the crop before tracing")
    ap.add_argument("--alphamax", type=float, default=0.0, help="0 keeps every corner; 1.334 rounds them")
    ap.add_argument("--turdsize", type=int, default=4, help="drop traced areas smaller than this")
    ap.add_argument("--opttolerance", type=float, default=0.2)
    ap.add_argument("--unit", type=int, default=1,
                    help="output grid; 1 snaps every point to a whole pixel and keeps the file small")
    a = ap.parse_args()

    src = Image.open(a.src).convert("RGB")
    if a.crop:
        W, H = src.size
        x0, y0, x1, y1 = [float(v) for v in a.crop.split(",")]
        bx0, by0, bx1, by1 = x0 * W, y0 * H, x1 * W, y1 * H
        bw, bh = bx1 - bx0, by1 - by0
        if bw / bh > a.aspect:
            nw = bh * a.aspect
            bx0 += (bw - nw) / 2
            bx1 = bx0 + nw
        else:
            nh = bw / a.aspect
            by0 += (bh - nh) / 2
            by1 = by0 + nh
        src = src.crop((int(bx0), int(by0), int(bx1), int(by1)))
    if a.scale != 1.0:
        src = src.resize((round(src.width * a.scale), round(src.height * a.scale)),
                         Image.Resampling.LANCZOS)

    # Quantising the image as it is spends the palette where the pixels are, and
    # on this die that is the bright middle: the shadows collapse to one entry and
    # whole dark blocks go flat. Clustering on a shadow-lifted copy gives the dark
    # end its share. The lift decides only which pixels group together; each
    # group's colour is then the mean of its ORIGINAL pixels, so nothing is
    # mapped back through the curve and no hue drifts.
    lifted = (src if a.shadow_gamma == 1.0 else
              src.point(lambda v: round(255 * (v / 255) ** (1 / a.shadow_gamma))))
    quant = lifted.quantize(colors=a.colours, method=getattr(Image.Quantize, a.method),
                            dither=Image.Dither.NONE)

    sums = {}
    for index, pixel in zip(quant.get_flattened_data() if hasattr(quant, "get_flattened_data") else quant.getdata(),
                           src.get_flattened_data() if hasattr(src, "get_flattened_data") else src.getdata()):
        acc = sums.setdefault(index, [0, 0, 0, 0])
        acc[0] += pixel[0]
        acc[1] += pixel[1]
        acc[2] += pixel[2]
        acc[3] += 1
    palette = {i: tuple(round(acc[c] / acc[3]) for c in range(3)) for i, acc in sums.items()}
    if a.palette_sat != 1.0:
        def saturate(c):
            grey = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
            return tuple(max(0, min(255, round(grey + (v - grey) * a.palette_sat))) for v in c)
        palette = {i: saturate(c) for i, c in palette.items()}
    if a.dim != 1.0:
        palette = {i: tuple(max(0, min(255, round(v * a.dim))) for v in c)
                   for i, c in palette.items()}

    counts = sorted(quant.getcolors(), key=lambda c: -c[0])     # (count, index)
    W, H = quant.size

    # the commonest colour becomes the ground, so nothing has to be traced for it
    ground = counts[0][1]
    rgb = lambda i: "#%02x%02x%02x" % palette[i]

    layers = []
    for count, index in counts[1:]:
        # build the mask in L: a point() on a palette image stays palette,
        # and converting that to bilevel goes through the palette instead
        mask = quant.point(lambda v, i=index: 0 if v == i else 255, "L").convert("1")
        ds = trace(mask, a.alphamax, a.turdsize, a.opttolerance, a.unit)
        if ds:
            layers.append((rgb(index), ds, count))

    # the viewBox keeps the traced coordinate space; width and height only say
    # how large a page lays the drawing out, and scaling it costs no sharpness
    vw = a.width or W
    vh = round(vw * H / W)
    crisp = ' shape-rendering="crispEdges"' if a.crisp else ''
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{vw}" height="{vh}"{crisp}>',
           f'<rect width="{W}" height="{H}" fill="{rgb(ground)}"/>',
           # potrace works bottom-up, so every traced path lives in a flipped space
           f'<g transform="translate(0,{H}) scale(1,-1)">']
    for colour, ds, _ in layers:
        d = " ".join(ds)
        out.append(f'<path fill="{colour}" d="{d}"/>')
    out += ["</g>", "</svg>"]
    svg = "\n".join(out)
    Path(a.out).write_text(svg)
    print(f"{a.out}: {W}x{H}, {len(layers) + 1} colours, "
          f"{sum(len(d) for _, ds, _ in layers for d in ds) // 1024} KiB of path data, "
          f"{len(svg) // 1024} KiB total")


if __name__ == "__main__":
    main()
