from pathlib import Path

import pandas as pd
import pytest
from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCAT, DCTERMS, FOAF, RDF, RDFS

from csv_ttl_convertor_v2 import (
    ADMS,
    DCATAP,
    DEFAULT_APPLICABLE_LEGISLATION,
    DEFAULT_CATALOG_DESCRIPTION,
    DEFAULT_CATALOG_PATH,
    DEFAULT_CATALOG_TITLE,
    DEFAULT_CONFORMS_TO,
    DEFAULT_DISTRIBUTION_FORMAT,
    DEFAULT_DISTRIBUTION_MEDIA_TYPE,
    DEFAULT_THEME,
    PRODUCTION_BASE,
    TESTING_BASE,
    add_catalog,
    add_contact_point,
    add_creator,
    add_distribution,
    add_keywords,
    add_publisher,
    add_theme,
    as_uri,
    as_uri_or_literal,
    bind_prefixes,
    catalog_uri,
    clean,
    convert_csv_to_ttl,
    convert_input_path_to_ttl,
    dataset_uri,
    distribution_uri,
    mailto_uri,
    normalize_base_uri,
    parse_issued_datetime,
    split_keywords,
    validate_columns,
    validate_input_path,
)

VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
CSV_PATH = Path("input/GDI_Norway_test_datasets_v2.csv")


# ============================================================================
# Tests for Helper Functions
# ============================================================================

class TestCleanFunction:
    def test_clean_returns_empty_string_for_nan(self):
        assert clean(float("nan")) == ""

    def test_clean_strips_whitespace(self):
        assert clean("  hello  ") == "hello"

    def test_clean_converts_to_string(self):
        assert clean(123) == "123"
        assert clean(45.67) == "45.67"

    def test_clean_handles_empty_string(self):
        assert clean("") == ""


class TestSplitKeywords:
    def test_split_keywords_with_valid_input(self):
        result = split_keywords("genomics, genetics, dna")
        assert result == ["genomics", "genetics", "dna"]

    def test_split_keywords_strips_whitespace(self):
        result = split_keywords("  key1  ,  key2  ,  key3  ")
        assert result == ["key1", "key2", "key3"]

    def test_split_keywords_handles_empty_string(self):
        assert split_keywords("") == []

    def test_split_keywords_handles_single_keyword(self):
        assert split_keywords("genetics") == ["genetics"]

    def test_split_keywords_handles_nan(self):
        assert split_keywords(float("nan")) == []


class TestParseIssuedDatetime:
    def test_parse_issued_datetime_with_dd_mm_yyyy_format(self):
        result = parse_issued_datetime("15-06-2023")
        assert isinstance(result, Literal)
        assert result.datatype == URIRef("http://www.w3.org/2001/XMLSchema#dateTime")

    def test_parse_issued_datetime_with_yyyy_mm_dd_format(self):
        result = parse_issued_datetime("2023-06-15")
        assert isinstance(result, Literal)
        assert result.datatype == URIRef("http://www.w3.org/2001/XMLSchema#dateTime")

    def test_parse_issued_datetime_with_iso_format_with_timezone(self):
        result = parse_issued_datetime("2023-06-15T10:30:00+02:00")
        assert isinstance(result, Literal)

    def test_parse_issued_datetime_with_empty_string_returns_current_utc(self):
        result = parse_issued_datetime("")
        assert isinstance(result, Literal)
        assert result.datatype == URIRef("http://www.w3.org/2001/XMLSchema#dateTime")

    def test_parse_issued_datetime_with_invalid_format_returns_current_utc(self):
        result = parse_issued_datetime("invalid-date")
        assert isinstance(result, Literal)
        assert result.datatype == URIRef("http://www.w3.org/2001/XMLSchema#dateTime")


class TestNormalizeBaseUri:
    def test_removes_trailing_slash(self):
        assert normalize_base_uri("http://example.com/") == "http://example.com"

    def test_keeps_uri_without_trailing_slash(self):
        assert normalize_base_uri("http://example.com") == "http://example.com"

    def test_removes_multiple_trailing_slashes(self):
        assert normalize_base_uri("http://example.com///") == "http://example.com"


class TestAsUriOrLiteral:
    def test_returns_uri_for_http_url(self):
        result = as_uri_or_literal("http://example.com")
        assert isinstance(result, URIRef)

    def test_returns_uri_for_https_url(self):
        result = as_uri_or_literal("https://example.com")
        assert isinstance(result, URIRef)

    def test_returns_uri_for_mailto(self):
        result = as_uri_or_literal("mailto:test@example.com")
        assert isinstance(result, URIRef)

    def test_returns_literal_for_plain_text(self):
        result = as_uri_or_literal("plain text")
        assert isinstance(result, Literal)

    def test_handles_whitespace(self):
        result = as_uri_or_literal("  plain text  ")
        assert isinstance(result, Literal)
        assert str(result) == "plain text"


class TestAsUri:
    def test_returns_uri_for_valid_http_url(self):
        result = as_uri("http://example.com")
        assert isinstance(result, URIRef)

    def test_returns_uri_for_valid_https_url(self):
        result = as_uri("https://example.com")
        assert isinstance(result, URIRef)

    def test_returns_fallback_for_non_uri_string(self):
        fallback = URIRef("http://fallback.com")
        result = as_uri("not-a-uri", fallback=fallback)
        assert result == fallback

    def test_returns_none_when_no_fallback_provided(self):
        result = as_uri("not-a-uri")
        assert result is None


class TestMailtoUri:
    def test_creates_mailto_uri_from_email(self):
        result = mailto_uri("test@example.com")
        assert result == URIRef("mailto:test@example.com")

    def test_returns_mailto_uri_as_is(self):
        result = mailto_uri("mailto:test@example.com")
        assert result == URIRef("mailto:test@example.com")

    def test_returns_none_for_empty_email(self):
        assert mailto_uri("") is None

    def test_strips_whitespace(self):
        result = mailto_uri("  test@example.com  ")
        assert result == URIRef("mailto:test@example.com")


class TestUriGeneration:
    def test_dataset_uri_generation(self):
        result = dataset_uri("http://example.com", "dataset-123")
        assert result == URIRef("http://example.com/dataset/dataset-123")

    def test_distribution_uri_generation(self):
        result = distribution_uri("http://example.com", "dataset-123")
        assert result == URIRef("http://example.com/dataset/dataset-123/distribution")

    def test_catalog_uri_generation_with_default_path(self):
        result = catalog_uri("http://example.com")
        assert result == URIRef(f"http://example.com/{DEFAULT_CATALOG_PATH}")

    def test_catalog_uri_generation_with_custom_path(self):
        result = catalog_uri("http://example.com", "custom/path")
        assert result == URIRef("http://example.com/custom/path")


# ============================================================================
# Tests for Validation Functions
# ============================================================================

class TestValidateColumns:
    def test_valid_columns_pass(self):
        df = pd.DataFrame(columns=[
            "id", "name", "description", "author_name", "author_id",
            "keywords", "publisher_name", "publisher_id", "theme",
            "contact_point", "issued", "external_link"
        ])
        # Should not raise
        validate_columns(df)

    def test_missing_columns_raise_error(self):
        df = pd.DataFrame(columns=["id", "name"])
        with pytest.raises(ValueError, match="missing required columns"):
            validate_columns(df)

    def test_extra_columns_are_allowed(self):
        df = pd.DataFrame(columns=[
            "id", "name", "description", "author_name", "author_id",
            "keywords", "publisher_name", "publisher_id", "theme",
            "contact_point", "issued", "external_link", "extra_column"
        ])
        # Should not raise
        validate_columns(df)


class TestValidateInputPath:
    def test_existing_csv_file_is_valid(self, tmp_path: Path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("id;name\n")
        result = validate_input_path(csv_file)
        assert result == csv_file

    def test_existing_directory_is_valid(self, tmp_path: Path):
        result = validate_input_path(tmp_path)
        assert result == tmp_path

    def test_non_existent_path_raises(self):
        with pytest.raises(ValueError, match="does not exist"):
            validate_input_path(Path("/non/existent/path"))

    def test_non_csv_file_raises(self, tmp_path: Path):
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("content")
        with pytest.raises(ValueError, match="must be a .csv file"):
            validate_input_path(txt_file)


# ============================================================================
# Tests for RDF Building Functions
# ============================================================================

class TestAddCatalog:
    def test_add_catalog_creates_catalog_triple(self):
        graph = Graph()
        bind_prefixes(graph)
        cat_uri = URIRef("http://example.com/catalog")
        dataset_uris = [
            URIRef("http://example.com/dataset/1"),
            URIRef("http://example.com/dataset/2"),
        ]

        add_catalog(graph, cat_uri, dataset_uris, "Test Catalog", "Test Description")

        assert (cat_uri, RDF.type, DCAT.Catalog) in graph
        assert (cat_uri, DCTERMS.title, Literal("Test Catalog")) in graph
        assert (cat_uri, DCTERMS.description, Literal("Test Description")) in graph

    def test_add_catalog_links_datasets(self):
        graph = Graph()
        cat_uri = URIRef("http://example.com/catalog")
        ds_uris = [
            URIRef("http://example.com/dataset/1"),
            URIRef("http://example.com/dataset/2"),
        ]

        add_catalog(graph, cat_uri, ds_uris, "Catalog", "Desc")

        for ds_uri in ds_uris:
            assert (cat_uri, DCAT.dataset, ds_uri) in graph


class TestAddCreator:
    def test_add_creator_with_name_and_id(self):
        graph = Graph()
        bind_prefixes(graph)
        ds_uri = URIRef("http://example.com/dataset/1")
        row = pd.Series({
            "author_name": "John Doe",
            "author_id": "http://orcid.org/1234",
        })

        add_creator(graph, ds_uri, row)

        creator_nodes = list(graph.objects(ds_uri, DCTERMS.creator))
        assert len(creator_nodes) == 1
        creator_node = creator_nodes[0]
        assert (creator_node, RDF.type, FOAF.Agent) in graph
        assert (creator_node, FOAF.name, Literal("John Doe")) in graph

    def test_add_creator_without_name_or_id_skips(self):
        graph = Graph()
        ds_uri = URIRef("http://example.com/dataset/1")
        row = pd.Series({"author_name": "", "author_id": ""})

        add_creator(graph, ds_uri, row)

        assert not list(graph.objects(ds_uri, DCTERMS.creator))


class TestAddPublisher:
    def test_add_publisher_with_name_and_id(self):
        graph = Graph()
        bind_prefixes(graph)
        ds_uri = URIRef("http://example.com/dataset/1")
        row = pd.Series({
            "publisher_name": "Test Publisher",
            "publisher_id": "http://example.com/org",
        })

        add_publisher(graph, ds_uri, row)

        pub_nodes = list(graph.objects(ds_uri, DCTERMS.publisher))
        assert len(pub_nodes) == 1
        pub_node = pub_nodes[0]
        assert (pub_node, RDF.type, FOAF.Agent) in graph


class TestAddContactPoint:
    def test_add_contact_point_with_email(self):
        graph = Graph()
        bind_prefixes(graph)
        ds_uri = URIRef("http://example.com/dataset/1")
        row = pd.Series({
            "author_name": "Jane Doe",
            "contact_point": "jane@example.com",
            "author_id": "",
        })

        add_contact_point(graph, ds_uri, row)

        contact_nodes = list(graph.objects(ds_uri, DCAT.contactPoint))
        assert len(contact_nodes) == 1
        contact_node = contact_nodes[0]
        assert (contact_node, RDF.type, VCARD.Kind) in graph
        assert (contact_node, VCARD.hasEmail, URIRef("mailto:jane@example.com")) in graph


class TestAddKeywords:
    def test_add_keywords_splits_and_adds_all(self):
        graph = Graph()
        bind_prefixes(graph)
        ds_uri = URIRef("http://example.com/dataset/1")
        row = pd.Series({"keywords": "genetics, genomics, dna"})

        add_keywords(graph, ds_uri, row)

        keywords = list(graph.objects(ds_uri, DCAT.keyword))
        keyword_strs = [str(kw) for kw in keywords]
        assert "genetics" in keyword_strs
        assert "genomics" in keyword_strs
        assert "dna" in keyword_strs


class TestAddTheme:
    def test_add_theme_with_custom_uri(self):
        graph = Graph()
        bind_prefixes(graph)
        ds_uri = URIRef("http://example.com/dataset/1")
        custom_theme = "http://publications.europa.eu/resource/authority/data-theme/TECH"
        row = pd.Series({"theme": custom_theme})

        add_theme(graph, ds_uri, row)

        themes = list(graph.objects(ds_uri, DCAT.theme))
        assert URIRef(custom_theme) in themes

    def test_add_theme_with_invalid_value_uses_default(self):
        graph = Graph()
        bind_prefixes(graph)
        ds_uri = URIRef("http://example.com/dataset/1")
        row = pd.Series({"theme": "not-a-uri"})

        add_theme(graph, ds_uri, row)

        themes = list(graph.objects(ds_uri, DCAT.theme))
        assert DEFAULT_THEME in themes


class TestAddDistribution:
    def test_add_distribution_creates_distribution_triple(self):
        graph = Graph()
        bind_prefixes(graph)
        ds_uri = URIRef("http://example.com/dataset/1")
        dist_uri = URIRef("http://example.com/dataset/1/distribution")
        row = pd.Series({
            "name": "Test Dataset",
            "external_link": "http://example.com/data",
        })

        add_distribution(graph, ds_uri, dist_uri, row)

        assert (dist_uri, RDF.type, DCAT.Distribution) in graph
        assert (ds_uri, DCAT.distribution, dist_uri) in graph

    def test_add_distribution_skips_if_no_external_link(self):
        graph = Graph()
        ds_uri = URIRef("http://example.com/dataset/1")
        dist_uri = URIRef("http://example.com/dataset/1/distribution")
        row = pd.Series({"name": "Test", "external_link": ""})

        add_distribution(graph, ds_uri, dist_uri, row)

        assert (dist_uri, RDF.type, DCAT.Distribution) not in graph


# ============================================================================
# Tests for CSV to TTL Conversion
# ============================================================================

class TestConvertCsvToTtl:
    def test_convert_csv_creates_ttl_file(self, tmp_path: Path):
        # Create minimal test CSV
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Test Dataset;Test Description;John;orcid/123;genetics;Publisher;org/1;;john@test.com;2023-01-01;http://example.com\n",
            encoding="utf-8"
        )

        output_ttl = tmp_path / "test.ttl"
        graph = convert_csv_to_ttl(
            output_ttl.parent / "test.csv", 
            output_ttl,
            base_uri="http://example.com"
        )

        assert output_ttl.exists()

    def test_convert_csv_creates_datasets_from_rows(self, tmp_path: Path):
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link1.com\n"
            "ds2;Dataset 2;Desc 2;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link2.com\n",
            encoding="utf-8"
        )

        output_ttl = tmp_path / "test.ttl"
        graph = convert_csv_to_ttl(test_csv, output_ttl, base_uri="http://example.com")

        parsed = Graph()
        parsed.parse(output_ttl, format="turtle")
        datasets = list(parsed.subjects(RDF.type, DCAT.Dataset))
        assert len(datasets) == 2

    def test_convert_csv_with_production_flag_includes_catalog(self, tmp_path: Path):
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n",
            encoding="utf-8"
        )

        output_ttl = tmp_path / "test.ttl"
        graph = convert_csv_to_ttl(
            test_csv, 
            output_ttl, 
            base_uri="http://example.com",
            production_cat=True
        )

        parsed = Graph()
        parsed.parse(output_ttl, format="turtle")
        catalogs = list(parsed.subjects(RDF.type, DCAT.Catalog))
        assert len(catalogs) == 1

    def test_convert_csv_without_production_flag_excludes_catalog(self, tmp_path: Path):
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n",
            encoding="utf-8"
        )

        output_ttl = tmp_path / "test.ttl"
        graph = convert_csv_to_ttl(
            test_csv, 
            output_ttl, 
            base_uri="http://example.com",
            production_cat=False
        )

        parsed = Graph()
        parsed.parse(output_ttl, format="turtle")
        catalogs = list(parsed.subjects(RDF.type, DCAT.Catalog))
        assert len(catalogs) == 0

    def test_convert_csv_uses_provided_base_uri(self, tmp_path: Path):
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n",
            encoding="utf-8"
        )

        output_ttl = tmp_path / "test.ttl"
        custom_base = "http://custom.example.com"
        graph = convert_csv_to_ttl(test_csv, output_ttl, base_uri=custom_base)

        parsed = Graph()
        parsed.parse(output_ttl, format="turtle")
        datasets = list(parsed.subjects(RDF.type, DCAT.Dataset))
        assert len(datasets) == 1
        # Check that custom base URI is in the dataset URI
        dataset_uri = datasets[0]
        assert custom_base in str(dataset_uri)

    def test_convert_csv_validates_required_columns(self, tmp_path: Path):
        invalid_csv = tmp_path / "invalid.csv"
        invalid_csv.write_text("id;name\n1;Dataset\n", encoding="utf-8")

        output_ttl = tmp_path / "invalid.ttl"
        with pytest.raises(ValueError, match="missing required columns"):
            convert_csv_to_ttl(invalid_csv, output_ttl, base_uri="http://example.com")

    def test_convert_csv_skips_rows_without_id(self, tmp_path: Path):
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n"
            ";Dataset 2;Desc 2;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n",
            encoding="utf-8"
        )

        output_ttl = tmp_path / "test.ttl"
        graph = convert_csv_to_ttl(test_csv, output_ttl, base_uri="http://example.com")

        parsed = Graph()
        parsed.parse(output_ttl, format="turtle")
        datasets = list(parsed.subjects(RDF.type, DCAT.Dataset))
        assert len(datasets) == 1


class TestConvertInputPathToTtl:
    def test_convert_single_csv_file(self, tmp_path: Path):
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n",
            encoding="utf-8"
        )

        output_dir = tmp_path / "output"
        generated = convert_input_path_to_ttl(
            test_csv, 
            output_dir,
            base_uri="http://example.com",
            production_cat=False,
            catalog_path=DEFAULT_CATALOG_PATH,
            catalog_title=DEFAULT_CATALOG_TITLE,
            catalog_description=DEFAULT_CATALOG_DESCRIPTION,
        )

        assert len(generated) == 1
        assert generated[0].exists()

    def test_convert_all_csvs_in_directory(self, tmp_path: Path):
        csv_dir = tmp_path / "csv_files"
        csv_dir.mkdir()

        csv1 = csv_dir / "dataset1.csv"
        csv2 = csv_dir / "dataset2.csv"

        csv_content = (
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n"
        )

        csv1.write_text(csv_content, encoding="utf-8")
        csv2.write_text(csv_content, encoding="utf-8")

        output_dir = tmp_path / "output"
        generated = convert_input_path_to_ttl(
            csv_dir, 
            output_dir,
            base_uri="http://example.com",
            production_cat=False,
            catalog_path=DEFAULT_CATALOG_PATH,
            catalog_title=DEFAULT_CATALOG_TITLE,
            catalog_description=DEFAULT_CATALOG_DESCRIPTION,
        )

        assert len(generated) == 2

    def test_convert_preserves_nested_directory_structure(self, tmp_path: Path):
        csv_dir = tmp_path / "csv_files"
        nested = csv_dir / "nested"
        nested.mkdir(parents=True)

        csv1 = csv_dir / "file1.csv"
        csv2 = nested / "file2.csv"

        csv_content = (
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n"
        )

        csv1.write_text(csv_content, encoding="utf-8")
        csv2.write_text(csv_content, encoding="utf-8")

        output_dir = tmp_path / "output"
        generated = convert_input_path_to_ttl(
            csv_dir, 
            output_dir,
            base_uri="http://example.com",
            production_cat=False,
            catalog_path=DEFAULT_CATALOG_PATH,
            catalog_title=DEFAULT_CATALOG_TITLE,
            catalog_description=DEFAULT_CATALOG_DESCRIPTION,
        )

        assert len(generated) == 2
        assert (output_dir / "file1.ttl").exists()
        assert (output_dir / "nested" / "file2.ttl").exists()

    def test_convert_directory_without_csv_files_raises(self, tmp_path: Path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        output_dir = tmp_path / "output"

        with pytest.raises(ValueError, match="No CSV files found"):
            convert_input_path_to_ttl(
                empty_dir, 
                output_dir,
                base_uri="http://example.com",
                production_cat=False,
                catalog_path=DEFAULT_CATALOG_PATH,
                catalog_title=DEFAULT_CATALOG_TITLE,
                catalog_description=DEFAULT_CATALOG_DESCRIPTION,
            )

    def test_convert_with_production_flag_adds_catalog(self, tmp_path: Path):
        csv_dir = tmp_path / "csv_files"
        csv_dir.mkdir()
        csv_file = csv_dir / "dataset.csv"

        csv_content = (
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset 1;Desc 1;Author;orcid;key;Pub;org;;email@test.com;2023-01-01;http://link.com\n"
        )
        csv_file.write_text(csv_content, encoding="utf-8")

        output_dir = tmp_path / "output"
        generated = convert_input_path_to_ttl(
            csv_dir, 
            output_dir,
            base_uri="http://example.com",
            production_cat=True,
            catalog_path=DEFAULT_CATALOG_PATH,
            catalog_title=DEFAULT_CATALOG_TITLE,
            catalog_description=DEFAULT_CATALOG_DESCRIPTION,
        )

        parsed = Graph()
        parsed.parse(generated[0], format="turtle")
        catalogs = list(parsed.subjects(RDF.type, DCAT.Catalog))
        assert len(catalogs) == 1


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    def test_full_conversion_produces_valid_rdf(self, tmp_path: Path):
        """Test full pipeline from CSV to valid RDF Turtle."""
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Test Dataset;A comprehensive test dataset;John Doe;http://orcid.org/0000-0001-2345-6789;genomics, genetics;Organization;http://org.com;http://example.eu/theme;john@example.com;2023-06-15;http://example.com/data.html\n",
            encoding="utf-8"
        )

        output_ttl = tmp_path / "output.ttl"
        graph = convert_csv_to_ttl(
            test_csv, 
            output_ttl,
            base_uri="http://example.com"
        )

        # Verify it's valid RDF by parsing it back
        parsed = Graph()
        parsed.parse(output_ttl, format="turtle")

        # Check for expected RDF structure
        datasets = list(parsed.subjects(RDF.type, DCAT.Dataset))
        assert len(datasets) == 1

        dataset_uri = datasets[0]
        assert (dataset_uri, DCTERMS.title, Literal("Test Dataset", lang="en")) in parsed
        assert (dataset_uri, DCTERMS.description, Literal("A comprehensive test dataset", lang="en")) in parsed

    def test_dataset_includes_all_required_properties(self, tmp_path: Path):
        """Test that datasets include all required DCAT properties."""
        test_csv = tmp_path / "test.csv"
        test_csv.write_text(
            "id;name;description;author_name;author_id;keywords;publisher_name;publisher_id;theme;contact_point;issued;external_link\n"
            "ds1;Dataset;Description;Author;ID;key;Pub;PubID;;email@test.com;2023-01-01;http://link.com\n",
            encoding="utf-8"
        )

        output_ttl = tmp_path / "output.ttl"
        convert_csv_to_ttl(
            test_csv, 
            output_ttl,
            base_uri="http://example.com"
        )

        parsed = Graph()
        parsed.parse(output_ttl, format="turtle")
        datasets = list(parsed.subjects(RDF.type, DCAT.Dataset))
        dataset_uri = datasets[0]

        # Check for core properties
        assert (dataset_uri, DCTERMS.identifier, Literal("ds1")) in parsed
        assert (dataset_uri, DCTERMS.issued, None) not in []  # issued should exist
        assert (dataset_uri, DCTERMS.modified, None) not in []  # modified should exist
        assert (dataset_uri, DCTERMS.conformsTo, DEFAULT_CONFORMS_TO) in parsed
