# Rapport PDF Generation

## Prerequisites

- [Pandoc](https://pandoc.org/installing.html)
- A LaTeX engine (e.g., [MiKTeX](https://miktex.org/) on Windows)

## Generate PDF

From this directory:

```bash
pandoc chapitre1.md -o chapitre1.pdf --include-in-header=toc-newpage.tex
```

## Files

| File | Purpose |
|---|---|
| `chapitre1.md` | Source content (Markdown) |
| `toc-newpage.tex` | LaTeX header — forces page break after table of contents |
| `chapitre1.pdf` | Generated output |
