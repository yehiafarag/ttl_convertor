import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, RDFS, XSD


# ---------------- Namespaces ---------------- #

ADMS = Namespace("http://www.w3.org/ns/adms#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
DCATAP = Namespace("http://data.europa.eu/r5r/")

# ---------------- Defaults ---------------- #

PRODUCTION_BASE = "http://gdi-norway.onemilliongenomes.eu"
TESTING_BASE = "http://gdi-norway.onemilliongenomes.eu"

DEFAULT_CATALOG_PATH = "catalog/2"

DEFAULT_CONFORMS_TO = URIRef("http://data.gdi.eu/core/p2/ExternallyGoverned")
DEFAULT_THEME = URIRef("http://publications.europa.eu/resource/authority/data-theme/HEAL")

DEFAULT_APPLICABLE_LEGISLATION = URIRef("https://data.europa.eu/eli/reg/2025/327/oj")
DEFAULT_DISTRIBUTION_FORMAT = "HTML"
DEFAULT_DISTRIBUTION_MEDIA_TYPE = "text/html"

DEFAULT_CATALOG_TITLE = "GDI Norway prod data catalog"
DEFAULT_CATALOG_DESCRIPTION = (
    "Prod datasets for the Genomic Data Infrastructure (GDI) of Norway."
)


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
    "external_link"
}


# ---------------- Helpers ---------------- #

def clean(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def now_utc_literal() -> Literal:
    return Literal(datetime.now(timezone.utc).isoformat(), datatype=XSD.dateTime)


def parse_issued_datetime(value: str) -> Literal:
    value = clean(value)

    if not value:
        return now_utc_literal()

    formats = [
        "%d-%m-%Y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
    ]

    for fmt in formats:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return Literal(parsed.isoformat(), datatype=XSD.dateTime)
        except ValueError:
            pass

    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return Literal(parsed.isoformat(), datatype=XSD.dateTime)
    except ValueError:
        return now_utc_literal()


def normalize_base_uri(base_uri: str) -> str:
    return base_uri.rstrip("/")


def resolve_base_uri(production: bool, explicit_base_uri: Optional[str] = None) -> str:
    if explicit_base_uri:
        return explicit_base_uri

    return PRODUCTION_BASE if production else TESTING_BASE


def dataset_uri(base_uri: str, dataset_id: str) -> URIRef:
    return URIRef(f"{normalize_base_uri(base_uri)}/dataset/{dataset_id}")

def distribution_uri(base_uri: str, dataset_id: str) -> URIRef:
    return URIRef(f"{normalize_base_uri(base_uri)}/dataset/{dataset_id}/distribution")

def catalog_uri(base_uri: str, catalog_path: str = DEFAULT_CATALOG_PATH) -> URIRef:
    catalog_path = catalog_path.strip("/")
    return URIRef(f"{normalize_base_uri(base_uri)}/{catalog_path}")


def split_keywords(raw_keywords: object) -> list:
    raw_keywords = clean(raw_keywords)
    return [kw.strip() for kw in raw_keywords.split(",") if kw.strip()]


def add_distribution(
        graph: Graph,
        dataset_ref: URIRef,
        distribution_ref: URIRef,
        row: pd.Series,
    ) -> None:
        external_link = clean(row.get("external_link"))

        # If no external link exists, do not create a distribution
        if not external_link:
            return

        dataset_name = clean(row.get("name"))

        graph.add((distribution_ref, RDF.type, DCAT.Distribution))

        graph.add(
            (
                distribution_ref,
                DCATAP.applicableLegislation,
                DEFAULT_APPLICABLE_LEGISLATION,
            )
        )

        graph.add((distribution_ref, DCTERMS.description, Literal("", lang="en")))
        graph.add((distribution_ref, DCTERMS.description, Literal("", lang="nl")))

        graph.add((distribution_ref, DCTERMS.format, Literal(DEFAULT_DISTRIBUTION_FORMAT)))
        graph.add((distribution_ref, DCTERMS.issued, now_utc_literal()))
        graph.add((distribution_ref, DCTERMS.modified, now_utc_literal()))

        graph.add(
            (
                distribution_ref,
                DCTERMS.title,
                Literal(f"Distribution for {dataset_name}", lang="en"),
            )
        )
        graph.add((distribution_ref, DCTERMS.title, Literal("", lang="nl")))

        graph.add((distribution_ref, DCAT.accessURL, URIRef(external_link)))
        graph.add((distribution_ref, DCAT.downloadURL, URIRef(external_link)))
        graph.add((distribution_ref, DCAT.mediaType, Literal(DEFAULT_DISTRIBUTION_MEDIA_TYPE)))

        rights_node = BNode()
        graph.add((rights_node, RDF.type, DCTERMS.RightsStatement))
        graph.add((rights_node, RDFS.label, Literal("", lang="en")))
        graph.add((rights_node, RDFS.label, Literal("", lang="nl")))

        graph.add((distribution_ref, DCTERMS.rights, rights_node))

        graph.add((dataset_ref, DCAT.distribution, distribution_ref))

def as_uri_or_literal(value: str):
    value = clean(value)

    if (
            value.startswith("http://")
            or value.startswith("https://")
            or value.startswith("mailto:")
    ):
        return URIRef(value)

    return Literal(value)


def as_uri(value: str, fallback: Optional[URIRef] = None) -> Optional[URIRef]:
    value = clean(value)

    if value.startswith("http://") or value.startswith("https://"):
        return URIRef(value)

    return fallback


def mailto_uri(email: str) -> Optional[URIRef]:
    email = clean(email)

    if not email:
        return None

    if email.startswith("mailto:"):
        return URIRef(email)

    return URIRef(f"mailto:{email}")


def bind_prefixes(graph: Graph) -> None:
    graph.bind("adms", ADMS)
    graph.bind("dcat", DCAT)
    graph.bind("dct", DCTERMS)
    graph.bind("foaf", FOAF)
    graph.bind("rdfs", RDFS)
    graph.bind("vcard", VCARD)
    graph.bind("xsd", XSD)
    graph.bind("dcatap", DCATAP)


def validate_columns(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(set(df.columns))

    if missing:
        raise ValueError(
            "CSV is missing required columns: "
            + ", ".join(sorted(missing))
        )


def validate_input_path(input_path: Path) -> Path:
    if not input_path.exists():
        raise ValueError(f"Input path does not exist: {input_path}")

    if input_path.is_file():
        if input_path.suffix.lower() != ".csv":
            raise ValueError(f"Input must be a .csv file, got: {input_path}")
        return input_path

    if input_path.is_dir():
        return input_path

    raise ValueError(f"Input path is neither a CSV file nor a directory: {input_path}")


def iter_csv_files(input_path: Path) -> list:
    if input_path.is_file():
        return [input_path]

    return sorted(p for p in input_path.rglob("*.csv") if p.is_file())


# ---------------- RDF builders ---------------- #

def add_catalog(
        graph: Graph,
        catalog_ref: URIRef,
        dataset_refs: Iterable[URIRef],
        title: str,
        description: str,
) -> None:
    graph.add((catalog_ref, RDF.type, DCAT.Catalog))
    graph.add((catalog_ref, DCTERMS.identifier, Literal(str(catalog_ref))))
    graph.add((catalog_ref, DCTERMS.title, Literal(title)))
    graph.add((catalog_ref, DCTERMS.description, Literal(description)))
    graph.add((catalog_ref, DCTERMS.issued, now_utc_literal()))

    for ds_ref in dataset_refs:
        graph.add((catalog_ref, DCAT.dataset, ds_ref))


def add_creator(graph: Graph, dataset_ref: URIRef, row: pd.Series) -> None:
    author_name = clean(row.get("author_name"))
    author_id = clean(row.get("author_id"))

    if not author_name and not author_id:
        return

    # Remove existing empty creator nodes from reader/exporter
    for creator_node in list(graph.objects(dataset_ref, DCTERMS.creator)):
        graph.remove((dataset_ref, DCTERMS.creator, creator_node))

        if isinstance(creator_node, BNode):
            graph.remove((creator_node, None, None))

    # Add complete creator node
    node = BNode()
    graph.add((node, RDF.type, FOAF.Agent))

    if author_id:
        graph.add((node, DCTERMS.identifier, as_uri_or_literal(author_id)))

    if author_name:
        graph.add((node, FOAF.name, Literal(author_name)))

    graph.add((dataset_ref, DCTERMS.creator, node))

    


def add_publisher(graph: Graph, dataset_ref: URIRef, row: pd.Series) -> None:
    publisher_name = clean(row.get("publisher_name"))
    publisher_id = clean(row.get("publisher_id"))

    if not publisher_name and not publisher_id:
        return

    node = BNode()
    graph.add((node, RDF.type, FOAF.Agent))

    if publisher_id:
        graph.add((node, DCTERMS.identifier, as_uri_or_literal(publisher_id)))

    if publisher_name:
        graph.add((node, FOAF.name, Literal(publisher_name)))

    graph.add((dataset_ref, DCTERMS.publisher, node))


def add_contact_point(graph: Graph, dataset_ref: URIRef, row: pd.Series) -> None:
    name = clean(row.get("author_name"))
    email = clean(row.get("contact_point"))
    uid = clean(row.get("author_id"))

    if not name and not email and not uid:
        return

    node = BNode()
    graph.add((node, RDF.type, VCARD.Kind))

    if name:
        graph.add((node, VCARD.fn, Literal(name)))

    email_ref = mailto_uri(email)
    if email_ref:
        graph.add((node, VCARD.hasEmail, email_ref))

    if uid:
        graph.add((node, VCARD.hasUID, as_uri_or_literal(uid)))

    graph.add((dataset_ref, DCAT.contactPoint, node))


def add_keywords(graph: Graph, dataset_ref: URIRef, row: pd.Series) -> None:
    for keyword in split_keywords(row.get("keywords")):
        graph.add((dataset_ref, DCAT.keyword, Literal(keyword, lang="en")))


def add_theme(graph: Graph, dataset_ref: URIRef, row: pd.Series) -> None:
    theme_value = clean(row.get("theme"))
    theme_ref = as_uri(theme_value, fallback=DEFAULT_THEME)

    if theme_ref:
        graph.add((dataset_ref, DCAT.theme, theme_ref))


def add_conforms_to(graph: Graph, dataset_ref: URIRef, row: pd.Series) -> None:
    conforms_value = clean(row.get("conformsTo"))

    if conforms_value:
        conforms_ref = as_uri(conforms_value, fallback=DEFAULT_CONFORMS_TO)
    else:
        conforms_ref = DEFAULT_CONFORMS_TO

    graph.add((dataset_ref, DCTERMS.conformsTo, conforms_ref))


def add_provenance(graph: Graph, dataset_ref: URIRef) -> None:
    node = BNode()
    graph.add((node, RDF.type, DCTERMS.ProvenanceStatement))
    graph.add((node, RDFS.label, Literal("", lang="en")))
    graph.add((node, RDFS.label, Literal("", lang="nl")))
    graph.add((dataset_ref, DCTERMS.provenance, node))


def add_version_notes(graph: Graph, dataset_ref: URIRef) -> None:
    graph.add((dataset_ref, ADMS.versionNotes, Literal("", lang="en")))
    graph.add((dataset_ref, ADMS.versionNotes, Literal("", lang="nl")))



def add_dataset(
        graph: Graph,
        dataset_ref: URIRef,
        row: pd.Series,
        base_uri: str,
) -> None:

    dataset_id = clean(row.get("id"))
    title = clean(row.get("name"))
    description = clean(row.get("description"))
    issued = parse_issued_datetime(clean(row.get("issued")))

    graph.add((dataset_ref, RDF.type, DCAT.Dataset))

    if dataset_id:
        graph.add((dataset_ref, DCTERMS.identifier, Literal(dataset_id)))

    if title:
        graph.add((dataset_ref, DCTERMS.title, Literal(title, lang="en")))

    if description:
        graph.add((dataset_ref, DCTERMS.description, Literal(description, lang="en")))

    graph.add((dataset_ref, DCTERMS.issued, issued))
    graph.add((dataset_ref, DCTERMS.modified, now_utc_literal()))

    add_conforms_to(graph, dataset_ref, row)
    add_creator(graph, dataset_ref, row)
    add_publisher(graph, dataset_ref, row)
    add_contact_point(graph, dataset_ref, row)
    add_keywords(graph, dataset_ref, row)
    add_theme(graph, dataset_ref, row)

    dist_ref = distribution_uri(base_uri, dataset_id)
    add_distribution(graph, dataset_ref, dist_ref, row)


# Optional fields from your compared target model
    add_provenance(graph, dataset_ref)
    add_version_notes(graph, dataset_ref)

    graph.add((DEFAULT_CONFORMS_TO, RDF.type, DCTERMS.Standard))


# ---------------- Conversion ---------------- #

def convert_csv_to_ttl(
        csv_path: Path,
        ttl_path: Path,
        base_uri: str,
        production_cat: bool = False,
        catalog_path: str = DEFAULT_CATALOG_PATH,
        catalog_title: str = DEFAULT_CATALOG_TITLE,
        catalog_description: str = DEFAULT_CATALOG_DESCRIPTION,
) -> Graph:
    df = pd.read_csv(csv_path, sep=";")
    validate_columns(df)

    base_uri = normalize_base_uri(base_uri)

    graph = Graph()
    bind_prefixes(graph)

    dataset_refs = []

    for _, row in df.iterrows():
        ds_id = clean(row.get("id"))
        if not ds_id:
            continue

        dataset_refs.append(dataset_uri(base_uri, ds_id))

    # Production only: add hardcoded catalog
    if production_cat:
        cat_ref = catalog_uri(base_uri, catalog_path)

        add_catalog(
            graph=graph,
            catalog_ref=cat_ref,
            dataset_refs=dataset_refs,
            title=catalog_title,
            description=catalog_description,
        )

    # Always add datasets
    for _, row in df.iterrows():
        ds_id = clean(row.get("id"))
        if not ds_id:
            continue

        ds_ref = dataset_uri(base_uri, ds_id)
        add_dataset(graph, ds_ref, row, base_uri)


    ttl_path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=str(ttl_path), format="turtle")

    return graph


def convert_input_path_to_ttl(
        input_path: Path,
        output_dir: Path,
        base_uri: str,
        production_cat: bool,
        catalog_path: str,
        catalog_title: str,
        catalog_description: str,
) -> list:
    validated_input = validate_input_path(input_path)
    csv_files = iter_csv_files(validated_input)

    if not csv_files:
        raise ValueError(f"No CSV files found in: {validated_input}")

    output_dir.mkdir(parents=True, exist_ok=True)

    generated_paths = []

    for csv_file in csv_files:
        if validated_input.is_dir():
            relative_parent = csv_file.parent.relative_to(validated_input)
        else:
            relative_parent = Path("")

        target_dir = output_dir / relative_parent
        ttl_path = target_dir / csv_file.with_suffix(".ttl").name

        convert_csv_to_ttl(
            csv_path=csv_file,
            ttl_path=ttl_path,
            base_uri=base_uri,
            production_cat=production_cat,
            catalog_path=catalog_path,
            catalog_title=catalog_title,
            catalog_description=catalog_description,
        )

        generated_paths.append(ttl_path)

    return generated_paths


# ---------------- CLI ---------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert GDI Norway CSV files into DCAT Turtle."
    )

    parser.add_argument(
        "input_path",
        nargs="?",
        default="input/",
        help="Input CSV file or folder containing CSV files. Default: input/",
    )

    parser.add_argument(
        "--output-dir",
        default="output",
        help="Output directory for TTL files. Default: output/",
    )

    parser.add_argument(
        "--production",
        action="store_true",
        default=False,
        help="Production mode: add hardcoded catalog block. Default is dataset-only testing mode.",
    )

    parser.add_argument(
        "--base-uri",
        default=None,
        help="Optional explicit base URI. Overrides production/testing base URI.",
    )

    parser.add_argument(
        "--catalog-path",
        default=DEFAULT_CATALOG_PATH,
        help=f"Catalog path after base URI. Default: {DEFAULT_CATALOG_PATH}",
    )

    parser.add_argument(
        "--catalog-title",
        default=DEFAULT_CATALOG_TITLE,
        help="Catalog title.",
    )

    parser.add_argument(
        "--catalog-description",
        default=DEFAULT_CATALOG_DESCRIPTION,
        help="Catalog description.",
    )

    args = parser.parse_args()

    base_uri = resolve_base_uri(
        production=args.production,
        explicit_base_uri=args.base_uri,
    )

    try:
        generated = convert_input_path_to_ttl(
            input_path=Path(args.input_path),
            output_dir=Path(args.output_dir),
            base_uri=base_uri,
            production_cat=args.production,
            catalog_path=args.catalog_path,
            catalog_title=args.catalog_title,
            catalog_description=args.catalog_description,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return

    mode = "production with catalog" if args.production else "testing dataset-only"

    for path in generated:
        print(f"Generated ({mode}): {path}")


if __name__ == "__main__":
    main()