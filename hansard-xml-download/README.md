# hansard-xml-download

Utility script for downloading Hansard PDFs from ParlInfo RSS/XML exports. The
folder is structured so it can be copied directly into a GitHub repository
named `hansard-xml-download`.

## Quick start (Colab-friendly)

```bash
pip install -r requirements.txt
python parlinfo_pdf_scraper.py \
  --xml-feed /path/to/search_results.xml \
  --output-dir parlinfo_pdfs \
  --max-files 3
```

* `--xml-feed` — path to the RSS XML you exported from ParlInfo
* `--xml-url` — alternatively fetch the XML directly from a ParlInfo search URL
* `--output-dir` — folder where PDFs will be saved
* `--max-files` — optional limit for testing
* `--min-delay`/`--max-delay` — tweak the human-like pause between requests

The script uses browser-like headers, retries, and polite delays to avoid
tripping bot protections. It parses the RSS XML, follows each result link, finds
the PDF URL on the page, and streams the file to disk with a friendly filename.

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Notes

* Feeds with many results may take a while due to the built-in delays.
* If a PDF link cannot be found on a page, the script skips that entry and
  continues with the rest.
