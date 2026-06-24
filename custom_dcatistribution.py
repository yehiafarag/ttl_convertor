from pydantic import Field
from rdflib import URIRef, DCAT
from sempyro.dcat import DCATDistribution
from sempyro.rdf_model import RDF_KEY, RDF_TYPE_KEY


class CustomDCATDistribution(DCATDistribution):
    """Custom DCAT Distribution class extending DCATDistribution.

    This class adds support for the access_url field, which provides a URI reference
    for accessing or requesting access to the dataset. It is used in the context of
    DCAT (Data Catalog Vocabulary) to describe distributions of datasets.

    Attributes:
        access_url (URIRef): URI reference for accessing or requesting access to the dataset.
    """

    access_url: URIRef = Field(
        ...,
        description="URI reference for accessing or requesting access to the dataset",
        json_schema_extra={RDF_KEY: DCAT.accessURL, RDF_TYPE_KEY: "uri"},

    )