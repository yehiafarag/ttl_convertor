from pathlib import Path

import pandas as pd
import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF

from csv_ttl_convertor_v2 import (
    ADMS,
    DCATAP,
    DEFAULT_ACCESS_RIGHTS,
    DEFAULT_APPLICABLE_LEGISLATION,
    DEFAULT_CONFORMS_TO,
    DEFAULT_HEALTH_CATEGORY,
    DEFAULT_LANGUAGE,
    ELI_LEGAL_RESOURCE,
    HEALTHDCATAP,
    convert_csv_to_ttl,
    convert_input_path_to_ttl,
)


CSV_PATH = Path("data_samples/GDI_Norway_test_datasets.csv")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")


def test_convert_creates_valid_ttl_with_expected_core_triples(tmp_path: Path) -> None:
    output_path = tmp_path / "catalog.ttl"
    graph = convert_csv_to_ttl(CSV_PATH, output_path)

    assert output_path.exists()

    parsed = Graph()
    parsed.parse(output_path, format="turtle")
    assert len(parsed) == len(graph)

    csv_df = pd.read_csv(CSV_PATH, sep=";")
    dataset_count = len(csv_df)

    dataset_subjects = list(parsed.subjects(RDF.type, DCAT.Dataset))
    distribution_subjects = list(parsed.subjects(RDF.type, DCAT.Distribution))
    assert len(dataset_subjects) == dataset_count
    assert len(distribution_subjects) == dataset_count

    row = csv_df.iloc[0]
    dataset_uri = URIRef(f"https://fdp.spain.ega-archive.org/datasets/{row['id']}")

    assert (dataset_uri, DCATAP.applicableLegislation, DEFAULT_APPLICABLE_LEGISLATION) in parsed
    assert (dataset_uri, HEALTHDCATAP.healthCategory, DEFAULT_HEALTH_CATEGORY) in parsed
    assert (dataset_uri, DCTERMS.accessRights, DEFAULT_ACCESS_RIGHTS) in parsed
    assert (dataset_uri, DCTERMS.conformsTo, DEFAULT_CONFORMS_TO) in parsed
    assert (dataset_uri, DCTERMS.language, DEFAULT_LANGUAGE) in parsed

    expected_keywords = {k.strip() for k in str(row["keywords"]).split(",") if k.strip()}
    actual_keywords = {
        str(obj)
        for obj in parsed.objects(dataset_uri, DCAT.keyword)
        if isinstance(obj, Literal)
    }
    assert expected_keywords.issubset(actual_keywords)

    assert (DEFAULT_CONFORMS_TO, RDF.type, DCTERMS.Standard) in parsed
    assert (DEFAULT_LANGUAGE, RDF.type, DCTERMS.LinguisticSystem) in parsed
    assert (DEFAULT_ACCESS_RIGHTS, RDF.type, DCTERMS.RightsStatement) in parsed
    assert (DEFAULT_APPLICABLE_LEGISLATION, RDF.type, ELI_LEGAL_RESOURCE) in parsed


def test_distribution_links_and_contact_point_are_present(tmp_path: Path) -> None:
    output_path = tmp_path / "catalog.ttl"
    parsed = convert_csv_to_ttl(CSV_PATH, output_path)

    csv_df = pd.read_csv(CSV_PATH, sep=";")
    row = csv_df.iloc[0]

    dataset_uri = URIRef(f"https://fdp.spain.ega-archive.org/datasets/{row['id']}")
    distribution_uri = URIRef(f"{dataset_uri}/distribution")

    assert (dataset_uri, DCAT.distribution, distribution_uri) in parsed
    assert (distribution_uri, DCATAP.applicableLegislation, DEFAULT_APPLICABLE_LEGISLATION) in parsed
    assert (distribution_uri, DCAT.downloadURL, URIRef(row["external_link"])) in parsed

    contact_nodes = list(parsed.objects(dataset_uri, DCAT.contactPoint))
    assert contact_nodes
    contact_node = contact_nodes[0]
    assert (contact_node, RDF.type, VCARD.Kind) in parsed
    assert (contact_node, VCARD.hasEmail, URIRef(f"mailto:{row['contact_point']}")) in parsed

    creator_nodes = list(parsed.objects(dataset_uri, DCTERMS.creator))
    assert creator_nodes
    creator_node = creator_nodes[0]
    assert (creator_node, RDF.type, FOAF.Agent) in parsed

    assert len(list(parsed.objects(dataset_uri, ADMS.versionNotes))) == 2


def test_missing_required_column_raises(tmp_path: Path) -> None:
    broken_csv = tmp_path / "broken.csv"
    broken_csv.write_text("id;name\n1;dataset\n", encoding="utf-8")

    with pytest.raises(ValueError, match="missing required columns"):
        convert_csv_to_ttl(broken_csv, tmp_path / "broken.ttl")


def test_convert_folder_creates_ttl_files_for_each_csv(tmp_path: Path) -> None:
    input_dir = tmp_path / "input"
    nested_dir = input_dir / "nested"
    nested_dir.mkdir(parents=True)

    csv1 = input_dir / "first.csv"
    csv2 = nested_dir / "second.csv"

    sample_df = pd.read_csv(CSV_PATH, sep=";")
    sample_df.to_csv(csv1, sep=";", index=False)
    sample_df.to_csv(csv2, sep=";", index=False)

    output_dir = tmp_path / "output"
    generated = convert_input_path_to_ttl(input_dir, output_dir)

    assert len(generated) == 2
    assert (output_dir / "first.ttl").exists()
    assert (output_dir / "nested" / "second.ttl").exists()

    parsed = Graph()
    parsed.parse(output_dir / "nested" / "second.ttl", format="turtle")
    assert len(list(parsed.subjects(RDF.type, DCAT.Dataset))) == len(sample_df)


def test_convert_folder_without_csv_files_raises(tmp_path: Path) -> None:
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    with pytest.raises(ValueError, match="No CSV files found"):
        convert_input_path_to_ttl(empty_dir, tmp_path / "output")
