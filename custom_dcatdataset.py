from sempyro.dcat import DCATDataset
from rdflib import URIRef
from pydantic import Field
from sempyro.rdf_model import RDF_KEY, RDF_TYPE_KEY
from rdflib.namespace import DCAT


class CustomDCATDataset(DCATDataset):
    """
    Extended DCAT Dataset with custom support access URL field.
    This class extends the standard DCATDataset to include an additional
    field for specifying a support access URL, which can be used to provide
    users with a link to request access to the dataset or obtain support.

    Attributes:
    support_access_url (URIRef): URI reference pointing to the support or access
    request endpoint for the dataset. Mapped to DCAT.accessURL in RDF.
   """
    support_access_url: URIRef = Field(
        ...,
        description="URI reference for accessing or requesting access to the dataset",
        json_schema_extra={RDF_KEY: DCAT.accessURL, RDF_TYPE_KEY: "uri"},

    )
