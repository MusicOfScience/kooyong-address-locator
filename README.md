# 📍 Kooyong Electorate Address Checker

A simple Streamlit app that lets you check if an address in Victoria falls within the federal electorate of Kooyong.

## 🚀 Features

- Enter any Victorian address
- See if it lies within Kooyong
- View the result on an interactive map
- Explore boundaries using Folium map styles

## 📦 Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

## 🏃 How to Run

Start the Streamlit app with:

```bash
streamlit run kooyong_app_address_checker.py
```

## 📥 Downloading ParlInfo PDFs from Colab

If you want to download Hansard PDFs from a ParlInfo RSS export, use the helper
script `parlinfo_pdf_scraper.py` (suitable for Google Colab):

```bash
python parlinfo_pdf_scraper.py \
  --xml-feed /path/to/search_results.xml \
  --output-dir parlinfo_pdfs \
  --max-files 3
```

The script reads the RSS XML, visits each result page using browser-like
headers, extracts the PDF link, and downloads the file with polite delays to
mimic a human visitor.

