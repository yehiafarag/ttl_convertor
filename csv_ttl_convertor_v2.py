import argparse
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, RDFS, XSD
from sempyro import LiteralField
from sempyro.dcat import DCATCatalog, DCATDataset

from arc.custom_dcatistribution import CustomDCATDistribution

ADMS = Namespace("http://www.w3.org/ns/adms#")
DCATAP = Namespace("http://data.europa.eu/r5r/")
HEALTHDCATAP = Namespace("http://healthdataportal.eu/ns/health#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")

DEFAULT_BASE = "https://fdp.spain.ega-archive.org"
DEFAULT_CATALOG_URI = f"{DEFAULT_BASE}/catalog"
DEFAULT_APPLICABLE_LEGISLATION = URIRef("https://data.europa.eu/eli/reg/2025/327/oj")
DEFAULT_HEALTH_CATEGORY = URIRef("http://data.gdi.eu/core/p2/HealthCategoryHumanGenetic")
DEFAULT_ACCESS_RIGHTS = URIRef("http://publications.europa.eu/resource/authority/access-right/PUBLIC")
DEFAULT_CONFORMS_TO = URIRef("http://data.gdi.eu/core/p2/ExternallyGoverned")
DEFAULT_LANGUAGE = URIRef("http://id.loc.gov/vocabulary/iso639-1/en")
DEFAULT_DATASET_TYPE = URIRef("https://publications.europa.eu/resource/authority/dataset-type/SYNTHETIC_DATA")
DEFAULT_THEME = URIRef("http://publications.europa.eu/resource/authority/data-theme/HEAL")
ELI_LEGAL_RESOURCE = URIRef("http://data.europa.eu/eli/ontology#LegalResource")

REQUIRED_COLUMNS = {
    "id",
    "name",
    "description",
    "author_name",
    "author_id",
    "keywords",
    "publisher_name",
    "publisher_id",
    "theme",
    "contact_point",
    "issued",
    "external_link",
}


def _clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _parse_issued_datetime(value: str) -> Literal:
    # CSV uses dd-mm-YYYY; fallback keeps a valid xsd:dateTime literal.
    try:
        parsed = datetime.strptime(value, "%d-%m-%Y").replace(tzinfo=timezone.utc)
    except ValueError:
        parsed = datetime.now(timezone.utc)
    return Literal(parsed.isoformat(), datatype=XSD.dateTime)


def _split_keywords(raw_keywords: str) -> list[str]:
    return [kw.strip() for kw in raw_keywords.split(",") if kw.strip()]


def _mailto_uri(email_or_uri: str) -> URIRef:
    if email_or_uri.startswith("mailto:"):
        return URIRef(email_or_uri)
    return URIRef(f"mailto:{email_or_uri}")


def _bind_prefixes(graph: Graph) -> None:
    graph.bind("adms", ADMS)
    graph.bind("dcat", DCAT)
    graph.bind("dcatap", DCATAP)
    graph.bind("dct", DCTERMS)
    graph.bind("foaf", FOAF)
    graph.bind("healthdcatap", HEALTHDCATAP)
    graph.bind("rdfs", RDFS)
    graph.bind("vcard", VCARD)
    graph.bind("xsd", XSD)


def _validate_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(set(df.columns))
    if missing:
        missing_sorted = ", ".join(sorted(missing))
        raise ValueError(f"CSV is missing required columns: {missing_sorted}")


def _validate_input_csv_path(csv_path: Path) -> Path:
    if csv_path.suffix.lower() != ".csv":
        raise ValueError(f"Input must be a .csv file, got: {csv_path}")
    if not csv_path.exists():
        raise ValueError(f"Input CSV does not exist: {csv_path}")
    if not csv_path.is_file():
        raise ValueError(f"Input CSV path is not a file: {csv_path}")
    return csv_path


def _validate_input_path(input_path: Path) -> Path:
    if not input_path.exists():
        raise ValueError(f"Input path does not exist: {input_path}")
    if input_path.is_file():
        if input_path.suffix.lower() != ".csv":
            raise ValueError(f"Input must be a .csv file, got: {input_path}")
        return input_path
    if input_path.is_dir():
        return input_path
    raise ValueError(f"Input path is neither a file nor a directory: {input_path}")


def _derive_output_ttl_path(csv_path: Path) -> Path:
    return csv_path.with_suffix(".ttl")


def _iter_csv_files(input_path: Path) -> list[Path]:
    if input_path.is_file():
        return [input_path]
    return sorted(p for p in input_path.rglob("*.csv") if p.is_file())


def convert_csv_to_ttl(csv_path: Path, ttl_path: Path, base_uri: str = DEFAULT_BASE) -> Graph:
    df = pd.read_csv(csv_path, sep=";")
    _validate_columns(df)

    catalog_uri = URIRef(DEFAULT_CATALOG_URI)
    graph = Graph()
    _bind_prefixes(graph)

    catalog = DCATCatalog(
        title=[LiteralField(value="GDI Spain-like data catalog")],
        description=[LiteralField(value="Catalog generated from GDI Norway CSV using SeMPyRO")],
        identifier=[str(catalog_uri)],
        release_date=datetime.now(timezone.utc).isoformat(),
    )
    graph += catalog.to_graph(catalog_uri)

    now_literal = Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)

    for _, row in df.iterrows():
        dataset_id = _clean(row["id"])
        dataset_uri = URIRef(f"{base_uri}/datasets/{dataset_id}")
        distribution_uri = URIRef(f"{dataset_uri}/distribution")

        dataset = DCATDataset(
            identifier=[dataset_id],
            title=[LiteralField(value=_clean(row["name"]), language="en")],
            description=[LiteralField(value=_clean(row["description"]), language="en")],
        )
        graph += dataset.to_graph(dataset_uri)
        graph.add((catalog_uri, DCAT.dataset, dataset_uri))

        graph.add((dataset_uri, DCATAP.applicableLegislation, DEFAULT_APPLICABLE_LEGISLATION))
        graph.add((dataset_uri, HEALTHDCATAP.healthCategory, DEFAULT_HEALTH_CATEGORY))
        graph.add((dataset_uri, DCTERMS.accessRights, DEFAULT_ACCESS_RIGHTS))
        graph.add((dataset_uri, DCTERMS.conformsTo, DEFAULT_CONFORMS_TO))
        graph.add((dataset_uri, DCTERMS.language, DEFAULT_LANGUAGE))
        graph.add((dataset_uri, DCTERMS.modified, now_literal))
        graph.add((dataset_uri, DCTERMS.issued, _parse_issued_datetime(_clean(row["issued"]))))
        graph.add((dataset_uri, DCTERMS.type, DEFAULT_DATASET_TYPE))

        theme_value = _clean(row["theme"])
        theme_uri = URIRef(theme_value) if theme_value.startswith("http") else DEFAULT_THEME
        graph.add((dataset_uri, DCAT.theme, theme_uri))

        for keyword in _split_keywords(_clean(row["keywords"])):
            graph.add((dataset_uri, DCAT.keyword, Literal(keyword, lang="en")))

        graph.add((dataset_uri, ADMS.versionNotes, Literal("", lang="en")))
        graph.add((dataset_uri, ADMS.versionNotes, Literal("", lang="nl")))

        creator_node = BNode()
        graph.add((creator_node, RDF.type, FOAF.Agent))
        graph.add((creator_node, DCTERMS.identifier, URIRef(_clean(row["author_id"]))))
        graph.add((creator_node, FOAF.name, Literal(_clean(row["author_name"])) ))
        graph.add((dataset_uri, DCTERMS.creator, creator_node))

        publisher_node = BNode()
        graph.add((publisher_node, RDF.type, FOAF.Agent))
        graph.add((publisher_node, DCTERMS.identifier, URIRef(_clean(row["publisher_id"]))))
        graph.add((publisher_node, FOAF.name, Literal(_clean(row["publisher_name"]))))
        graph.add((dataset_uri, DCTERMS.publisher, publisher_node))

        contact_node = BNode()
        graph.add((contact_node, RDF.type, VCARD.Kind))
        graph.add((contact_node, VCARD.fn, Literal(f"Contact for {_clean(row['publisher_name'])}")))
        graph.add((contact_node, VCARD.hasEmail, _mailto_uri(_clean(row["contact_point"]))))
        graph.add((dataset_uri, DCAT.contactPoint, contact_node))

        distribution = CustomDCATDistribution(
            title=[LiteralField(value=f"Distribution for {_clean(row['name'])}", language="en")],
            description=[LiteralField(value="", language="en"), LiteralField(value="", language="nl")],
            access_url=URIRef(_clean(row["external_link"])),
        )
        graph += distribution.to_graph(distribution_uri)

        graph.add((dataset_uri, DCAT.distribution, distribution_uri))
        graph.add((distribution_uri, DCATAP.applicableLegislation, DEFAULT_APPLICABLE_LEGISLATION))
        graph.add((distribution_uri, DCTERMS.issued, now_literal))
        graph.add((distribution_uri, DCTERMS.modified, now_literal))
        graph.add((distribution_uri, DCTERMS.format, Literal("HTML")))
        graph.add((distribution_uri, DCAT.downloadURL, URIRef(_clean(row["external_link"]))))
        graph.add((distribution_uri, DCAT.mediaType, Literal("text/html")))

        rights_node = BNode()
        graph.add((rights_node, RDF.type, DCTERMS.RightsStatement))
        graph.add((rights_node, RDFS.label, Literal("", lang="en")))
        graph.add((rights_node, RDFS.label, Literal("", lang="nl")))
        graph.add((distribution_uri, DCTERMS.rights, rights_node))

        graph.add((URIRef(_clean(row["external_link"])), RDF.type, RDFS.Resource))

    graph.add((DEFAULT_CONFORMS_TO, RDF.type, DCTERMS.Standard))
    graph.add((DEFAULT_LANGUAGE, RDF.type, DCTERMS.LinguisticSystem))
    graph.add((DEFAULT_ACCESS_RIGHTS, RDF.type, DCTERMS.RightsStatement))
    graph.add((DEFAULT_APPLICABLE_LEGISLATION, RDF.type, ELI_LEGAL_RESOURCE))

    ttl_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(ttl_path, format="turtle")
    return graph


def convert_input_path_to_ttl(input_path: Path, output_dir: Path, base_uri: str = DEFAULT_BASE) -> list[Path]:
    validated_input = _validate_input_path(input_path)
    csv_files = _iter_csv_files(validated_input)
    if not csv_files:
        raise ValueError(f"No CSV files found in: {validated_input}")

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: list[Path] = []

    for csv_file in csv_files:
        relative_parent = csv_file.parent.relative_to(validated_input) if validated_input.is_dir() else Path("")
        target_dir = output_dir / relative_parent
        ttl_path = target_dir / csv_file.with_suffix(".ttl").name
        convert_csv_to_ttl(csv_file, ttl_path, base_uri=base_uri)
        generated_paths.append(ttl_path)

    return generated_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert GDI CSV into DCAT Turtle")
    parser.add_argument(
        "input_path",
        nargs="?",
        default="input/",
        help="Input CSV file or folder containing CSV files",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Optional output directory (defaults to output/)",
    )
    parser.add_argument(
        "--base-uri",
        default=DEFAULT_BASE,
        help="Base URI for generated dataset resources",
    )

    args = parser.parse_args()

    try:
        input_path = _validate_input_path(Path(args.input_path))
    except ValueError as exc:
        parser.error(str(exc))

    output_dir = Path(args.output_dir) if args.output_dir else Path("output")

    if input_path.is_file():
        output_path = _derive_output_ttl_path(input_path)
        if args.output_dir:
            output_path = output_dir / output_path.name
        convert_csv_to_ttl(input_path, output_path, base_uri=args.base_uri)
        return

    convert_input_path_to_ttl(input_path, output_dir, base_uri=args.base_uri)


if __name__ == "__main__":
    main()
