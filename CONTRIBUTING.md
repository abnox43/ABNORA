# Contributing to ABNORA

Thanks for your interest. ABNORA is a small, readable desktop application;
patches that keep it that way are most welcome.

## Development setup

```bash
sudo apt install python3 python3-venv python3-pip \
                 python3-pyside6.qtwidgets python3-pyside6.qtgui python3-pymupdf
git clone https://github.com/abnora/abnora.git
cd abnora
python3 -m venv --system-site-packages .venv
source .venv/bin/activate
pip install -e ".[dev]"
python main.py
```

## Before you submit

```bash
pytest                      # must pass (runs offscreen)
python scripts/capture_screenshots.py   # optional, if you changed visuals
```

## Guidelines

- **Keep the layering.** `src/abnora/pdf/` and `src/abnora/storage/` must not
  import Qt widgets. UI code must not hard-code colors — use theme tokens.
- **Add tests** for anything in the engine or storage layers. GUI changes
  should be covered by a test in `tests/test_gui_smoke.py` when practical.
- **No network.** ABNORA is local-first; additions must not make requests or
  add telemetry.
- **Performance.** Never render or parse on the UI thread. Use the existing
  `PdfRenderer` worker path.
- **Accessibility.** Respect reduced motion, keep focus indicators visible,
  and maintain readable contrast in every theme.
- **Commit style.** Imperative mood, one logical change per PR, with a short
  rationale in the body.

## Reporting bugs

Include your Debian/Ubuntu version, Python and PySide6 versions, the PDF
program that produced the file (if known), and steps to reproduce. Sample PDFs
that trigger crashes are extremely helpful (please use a non-confidential file).
