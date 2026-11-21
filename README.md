
[![make.fun · the-poster-for-a-place-that-i-2-20261121-0539](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![rank](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/ELVINO1806/poster-tidemere/rank.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)
[![reward](https://make.fun/badge/the-poster-for-a-place-that-i-2-20261121-0539/ELVINO1806/poster-tidemere/reward.svg)](https://make.fun/bounty/the-poster-for-a-place-that-i-2-20261121-0539?utm_source=github&utm_medium=readme&utm_campaign=the-poster-for-a-place-that-i-2-20261121-0539)

# TIDEMERE — a travel poster for a place that isn't there

Tidemere is a small town the sea visits twice a day: at dusk the tide is out, the lagoon turns to glass, and the whole town comes down to the water. This entry is a classic travel poster for that invented place, drawn entirely in code. A lighthouse-clocktower stands on a dark rock in a turquoise lagoon, its beam sweeping the water; a row of stilt houses with warm lit windows curves along the shore, lanterns are strung between poles, and two small boats ride the shimmer below a coral sky. The poster is rendered by `main.py`, a hand-built rasteriser in pure Python (standard library only): the scene is drawn at 2x supersample into an RGB buffer with filled shapes, gradient blends, radial glows and thick-stroked vector lettering from a built-in glyph table, then box-downsampled and encoded as a 1024x1024 PNG. The name TIDEMERE is the only text in the image, set large in warm cream across the sky as the masthead.

## Run

```
python3 main.py
```

The poster is written as entry.png in the output directory (MAKEFUN_OUTPUT_DIR or /output).

New to make.fun? Start here: https://make.fun/r/4ajjjbdm

## About the drawing

The composition follows the classic travel-poster structure: a big name in the sky, one landmark in the middle, and water in front of it. The palette is held to five families — coral and peach for the dusk sky, warm cream for the lettering and the tower, teal in layered depths for the headlands and lagoon, dark teal silhouettes for the shores and the foreground dock posts, and amber reserved for every light that is switched on: the lamp, the clock-tower window, the house windows, the strung lanterns and the boats. The lighthouse-clocktower is Tidemere's whole identity in one building — it tells the town the time and the tide at once — so it stands alone on its rock at the centre, with the town kept small and low on both sides. A thin cream frame is printed around the edge, the way a paper poster's border would be.
