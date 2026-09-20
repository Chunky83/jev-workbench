# README welcome animation

Two separate six-second variants are also available:
`jev-welcome-stumble.gif` and `jev-welcome-spin.gif`, each with a matching PNG,
MP4, and motion source in `scripts/`. See [the comparison](../animation-variants.md).

`jev-welcome.gif` is an 800 × 340, 25 fps, 7-second silent loop made with
Higgsfield's native Higgsedit renderer from the original Workbench icon.
The character has no icon tile: it pops in, stumbles through two uneven steps,
catches its balance, makes a full 360-degree turn, settles into place, and
winks at the viewer as the mint star appears. Squash and stretch, a small
landing wobble, and a subtle ground shadow give the movement weight.
`jev-welcome.png` provides a still alternative.

The previously approved wink animation and its matching source are preserved
in [versions/wink-v1](versions/wink-v1/README.md).

`jev-character.png` is the transparent character with empty goggle lenses;
the eyes and pupils are separate animated shapes in the motion source.
`jev-star.png` is the original mint star isolated for its final pop.
Both assets were separated from the original artwork in the Higgsfield sandbox.

The editable motion source is `scripts/jev-welcome.jsx`. With Higgsedit installed,
run it from the repository root:

```sh
higgsedit build scripts/jev-welcome.jsx
ffmpeg -i build/jev-welcome-animation/renders/jev-welcome.mp4 -filter_complex "[0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle" -loop 0 docs/assets/jev-welcome.gif
```

The original icon's provenance is recorded in `desktop/assets/README.md`.
