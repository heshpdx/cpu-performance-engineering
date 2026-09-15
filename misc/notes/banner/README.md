# Banner

`misc/banner-pinnacle-ridge.avif` at the top of the README is a photograph
of the polysilicon layer of AMD's Zen+ Pinnacle Ridge die, the Ryzen 5 2600.
The two gold blocks are its core complexes; the teal between and around them
is the rest of the die.

The crop is the centre band at full width, resized to 3000x1100, then
calmed and encoded as AVIF at quality 64.

Source: Wikimedia Commons,
`AMD@12nm@Zen+@Pinnalce Ridge@Ryzen 5 2600@YD2600BBM6IAF UA 1841PGT
9HIO968W80588 DSCx3 polysilicon@5x.jpg`, 19700x8660, **CC0**. The render
works from the 3840-wide scaled copy, which is more than the banner needs.

    band = width / (3000 / 1100)
    crop = (0, (height - band) // 2, width, (height + band) // 2)
    im = crop.resize((3000, 1100))
    im = ImageEnhance.Color(im).enhance(0.55)
    im = ImageEnhance.Contrast(im).enhance(0.88)
    im = ImageEnhance.Brightness(im).enhance(0.90)
    im.save("banner.avif", quality=64)

Those three numbers are the only change to the photograph. At full strength
a polysilicon shot is genuinely hard to look at for long: the gold sits
against a near-cyan at close to full saturation, and a banner is something a
reader passes over on the way to the text rather than studies. Halving the
saturation and easing the contrast keeps the gold and teal legible while
removing the glare entirely. This is about as far as it goes; much below
0.55 the two stop separating and it reads as one grey-green field.

The file is named after its source rather than just `banner`. GitHub's asset
cache serves a stale copy for some time after a file at a known path
changes, so a new banner takes a new path and appears immediately.

## Why this one and not a traced die

Earlier banners ran their source through one of two renderers kept here:
`render.py` draws an image as a grid of hex glyphs coloured by what sits
under each cell, and `vectorise.py` traces it to flat vector shapes, which
makes it resolution-free.

Neither is used now, and the reason is worth recording. Both were tried on
several die photographs and all of them came out muddy. The cause was the
sources, not the treatments: an ordinary microscope capture of a finished
die is a low-contrast brown field with no structure at banner width, and no
amount of saturation rescues that. A polysilicon-layer shot is lit so that
thin-film interference gives hard, saturated colour, which is why this one
needs no treatment at all.

## Earlier banners

The design record holds each one with its licence.

- IBM POWER3-II and Sun UltraSPARC II, both Wikimedia Commons, both CC0,
  traced with `vectorise.py`. Dropped: see above.
- A photograph of a quad-core CPU die, traced and plain. Dropped because
  its origin and licence were never established.
- Intel Pentium II Dixon, Wikimedia Commons, 22036x13288, by Martijn Boer,
  public domain, as a hex-glyph grid with its SRAM arrays recoloured away
  from the gold top-layer metal.
- Hokusai's *Under the Wave off Kanagawa*, the Met's CC0 scan, object 45434,
  which was the first banner this repository shipped.
