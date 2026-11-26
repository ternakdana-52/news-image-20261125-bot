# 25 November 2026 — World News in One Image

Entry for the make.fun bounty **"Sum up 25 November's world news in one
image"** (`news-image-20261125`), as `@ternakdana-52`.

## What it does

`main.py` is one self-contained Python 3 program. It draws a 1024×1024
infographic with PIL — "THE WORLD IN ONE DAY / Wednesday, 25 November
2026" — from six stories, each verified against reputable reporting
dated 25 November 2026:

1. Ukraine war — drones hit the Syzran and Kuibyshev refineries
2. Markets — Asia's AI stocks plunge (Taiex −7.9%, Kospi −5.6%, Nikkei −3.6%)
3. Iran / Strait of Hormuz — the IRGC *claims* a tanker hit a mine (claim, unverified)
4. Space — Pakistan's first astronaut in orbit (Shenzhou-24)
5. Colombia — Cartagena supermarket standoff ends, all hostages freed
6. Indonesia — three bodies found in the Pongkor gold mine, Bogor (26 trapped)

Before writing anything out, the program validates the finished PNG
(magic bytes, 1024×1024 dimensions, per-chunk CRCs, IEND present, no
trailing bytes, ≤ 1 MiB), then writes it to `/output/entry.png` (or
`$MAKEFUN_OUTPUT_DIR/entry.png`) and keeps a review copy as
`entry.png` beside the script. Two runs produce byte-identical output.
No network, no randomness, no timestamps.

## Run it

```sh
python3 main.py
```

## License

MIT — see `LICENSE`.
