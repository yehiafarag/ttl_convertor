# GDI Norway - CSV to TTL Converter

A Python command-line tool to convert CSV metadata files into RDF Turtle format following DCAT/DCAT-AP standards. 

This converter targets GDI (Genomic Data Infrastructure) datasets for Norway, generating DCAT Catalog and Dataset triples with comprehensive metadata properties.

## Features

- **Single file or batch conversion**: Convert a single CSV file or recursively process all CSV files in a directory
- **Flexible URIs**: Supports both production and testing base URIs, with optional custom URIs
- **Catalog support**: Optionally generate a DCAT Catalog wrapper around datasets (production mode)
- **RDF validation**: Generated Turtle files are valid RDF and can be parsed and queried
- **Comprehensive metadata**: Includes contact points, creators, publishers, keywords, themes, and external access links
- **Folder structure preservation**: Maintains nested directory structure when batch processing
- **No accidental overwrite**: If an output file already exists, a new file is created with an index suffix (for example, `dataset_1.ttl`)
- **Dataset type fallback**: If the CSV does not include a `type` column, the converter adds `dct:type` with the synthetic dataset URI

## Quick Start

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Run the converter

Basic usage (testing mode, no catalog):
```bash
python3 csv_ttl_convertor_v2.py input/GDI_Norway_test_datasets_v2.csv
```

Production mode with catalog:
```bash
python3 csv_ttl_convertor_v2.py input/GDI_Norway_test_datasets_v2.csv --production
```

Batch convert all CSV files in a directory:
```bash
python3 csv_ttl_convertor_v2.py input/ --output-dir output/ --production
```

## Command-line Options

```
usage: csv_ttl_convertor_v2.py [-h] [--output-dir OUTPUT_DIR] [--production]
                               [--base-uri BASE_URI] [--catalog-path CATALOG_PATH]
                               [--catalog-title CATALOG_TITLE]
                               [--catalog-description CATALOG_DESCRIPTION]
                               [input_path]

Convert GDI Norway CSV files into DCAT Turtle.

positional arguments:
  input_path            Input CSV file or folder containing CSV files. Default: input/

optional arguments:
  -h, --help            show this help message and exit
  --output-dir OUTPUT_DIR
                        Output directory for TTL files. Default: output/
  --production          Production mode: add hardcoded catalog block. Default is
                        dataset-only testing mode.
  --base-uri BASE_URI   Optional explicit base URI. Overrides production/testing base URI.
  --catalog-path CATALOG_PATH
                        Catalog path after base URI. Default: catalog/2
  --catalog-title CATALOG_TITLE
                        Catalog title.
  --catalog-description CATALOG_DESCRIPTION
                        Catalog description.
```

## CSV Format

The input CSV must use **semicolon (`;`) as the field separator**.

### Required Columns

All of the following columns must be present in the input CSV:

| Column | Description | Example |
|--------|-------------|---------|
| id | Dataset identifier | dataset-001 |
| name | Dataset title | GCNV Dataset |
| description | Dataset description | Copy number variations from... |
| author_name | Creator/author name | John Doe |
| author_id | Creator identifier (URI or ID) | http://orcid.org/0000-0001-2345-6789 |
| keywords | Comma-separated keywords | genomics, genetics, dna |
| publisher_name | Publishing organization name | GDI Norway |
| publisher_id | Publisher identifier (URI or ID) | http://example.org/publisher |
| theme | Dataset theme/category (optional URI) | http://publications.europa.eu/resource/authority/data-theme/HEAL |
| contact_point | Contact email address | contact@example.org |
| issued | Publication date | 2023-06-15 or 15-06-2023 |
| external_link | URL to access/download the dataset | http://example.org/data.html |
| type | Optional dataset type URI | https://publications.europa.eu/resource/authority/dataset-type/TEST_DATASET |

### Date Formats Supported

The issued column accepts multiple date formats:
- DD-MM-YYYY (e.g., 15-06-2023)
- YYYY-MM-DD (e.g., 2023-06-15)
- YYYY-MM-DDTHH:MM:SS with timezone (ISO 8601, e.g., 2023-06-15T10:30:00+02:00)
- Empty or invalid dates default to current UTC time

## Output Format

### Testing Mode (default)
Generates datasets only without a catalog wrapper:
```turtle
@prefix dcat: <http://www.w3.org/ns/dcat#> .
@prefix dct: <http://purl.org/dc/terms/> .

<http://gdi-norway.onemilliongenomes.eu/dataset/dataset-001>
  a dcat:Dataset ;
  dct:identifier "dataset-001" ;
  dct:title "My Dataset"@en ;
  dct:description "Dataset description"@en ;
  dct:creator [ ... ] ;
  dcat:distribution [ ... ] ;
  ...
  .
```

### Production Mode (with --production flag)
Generates a catalog containing multiple datasets:
```turtle
<http://gdi-norway.onemilliongenomes.eu/catalog/2>
  a dcat:Catalog ;
  dct:title "GDI Norway prod data catalog" ;
  dcat:dataset <.../dataset-001> ;
  dcat:dataset <.../dataset-002> ;
  ...
  .
```

## Testing

Run the test suite:
```bash
python3 -m pytest tests/ -v
```

Run with coverage:
```bash
python3 -m pytest tests/ --cov=csv_ttl_convertor_v2 --cov-report=html
```

### Test Coverage

The test suite includes:

- **Helper function tests**: String cleaning, keyword parsing, date parsing, URI generation
- **Validation tests**: Required column validation, input path validation
- **RDF building tests**: Catalog creation, creator/publisher/contact addition, theme handling, distribution creation
- **Conversion tests**: Single file conversion, batch conversion, URI customization, catalog generation
- **Integration tests**: Full pipeline validation, RDF structure validation

## RDF Vocabularies Used

- **DCAT** - Data Catalog Vocabulary (datasets, distributions, catalogs)
- **DCTERMS** - Dublin Core Terms (titles, descriptions, dates, creators, publishers)
- **FOAF** - Friend of a Friend (agent names and organization information)
- **VCARD** - vCard (contact point details)
- **ADMS** - Asset Description Metadata Schema (version notes)
- **DCATAP** - DCAT Application Profile extensions
- **XSD** - XML Schema (for typed literals like dates)

