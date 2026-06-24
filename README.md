# ttl_convertor

CSV to TTL converter for GDI metadata using SeMPyRO and DCAT/HealthDCAT-AP style vocabularies.

## What this project does

- Reads CSV metadata files (same format as `data_samples/GDI_Norway_test_datasets.csv`).
- Converts records to RDF Turtle (`.ttl`) using SeMPyRO and `rdflib`.
- Supports converting:
  - a single CSV file, or
  - a folder of CSV files recursively.
- Writes generated TTL files to an output folder.

## Quick start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Converter script

Main script: `csv_ttl_convertor_v2.py`

### 1) Convert one CSV file

```bash
python3 csv_ttl_convertor_v2.py "data_samples/GDI_Norway_test_datasets.csv"
```

- By default, this creates `data_samples/GDI_Norway_test_datasets.ttl`.

### 2) Convert all CSV files in a folder

```bash
python3 csv_ttl_convertor_v2.py data_samples --output-dir output
```

- Finds all `*.csv` files recursively.
- Creates matching `.ttl` filenames in `output/`.
- Keeps nested folder structure when input has subfolders.

### 3) Optional base URI override

```bash
python3 csv_ttl_convertor_v2.py data_samples --output-dir output --base-uri "https://example.org"
```

## Validation and tests

Run tests:

```bash
python3 -m pytest -q
```

Tests cover:
- TTL generation and parse validation
- expected DCAT/HealthDCAT-AP triples
- distribution and contact-point links
- required-column validation
- folder batch conversion behavior

## Required CSV columns

The converter validates these columns before generating output:

- `id`
- `name`
- `description`
- `author_name`
- `author_id`
- `keywords`
- `publisher_name`
- `publisher_id`
- `theme`
- `contact_point`
- `issued`
- `external_link`

## Technology and model

- SeMPyRO for RDF model objects (`DCATCatalog`, `DCATDataset`, custom distribution)
- `rdflib` for graph operations and extra triples
- DCAT-based output with related vocabularies (`dcat`, `dct`, `foaf`, `vcard`, `adms`, `dcatap`, `healthdcatap`)

## Legacy scripts

Older scripts are kept for reference:

```bash
python3 csvtottl.py
python3 csvtottl_2.py
```
