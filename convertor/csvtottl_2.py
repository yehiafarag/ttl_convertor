import pandas as pd
from rdflib import URIRef, DCTERMS, DCAT
from sempyro import LiteralField
from sempyro.dcat import DCATCatalog
from sempyro.vcard import VCard

from custom_dcatdataset import CustomDCATDataset

BASE = "http://gdi-norway.onemilliongenomes.eu"
CATALOG_URI = f"{BASE}/catalog/1"
CATALOG_SUBJ = URIRef(CATALOG_URI)

df = pd.read_csv("data_samples/GDI_Norway_test_datasets.csv", sep=";")

catalog = DCATCatalog(
    title=[LiteralField(value="GDI Norway test data catalog")],
    description=[LiteralField(value="Test datasets for the Genomic Data Indrastructur (GDI) of Norway.")],
    identifier=[CATALOG_URI],
    release_date="2024-04-30T00:00:00",
)
g = catalog.to_graph(URIRef(CATALOG_URI))

for _, r in df.iterrows():
    ds_id = str(r["id"]).strip()
    ds_uri = URIRef(f"{BASE}/dataset/{ds_id}")

    # 1 Creator (vCard)

    author_name = str(r["author_name"]).strip()
    author_id = str(r["author_id"]).strip()
    vcard_uri = URIRef(f"{BASE}/vcard/{author_id}")

    creator = VCard(
        formatted_name=[str(r["author_name"]).strip()],
        hasUID=author_id,
    )
    # Add dataset to graph
    g += creator.to_graph(ds_uri)

    # Link dataset to catalog
    g.add((ds_uri,DCTERMS.creator, vcard_uri))

    # 2 Dataset
    # case where we want to use the custom dataset class with support_access_url field
    dataset = CustomDCATDataset(
        identifier=[ds_id],
        title=[LiteralField(value=str(r["name"]).strip(), language="en")],
        description=[LiteralField(value=str(r["description"]).strip(), language="en")],
        creator=[creator],
        support_access_url=URIRef("mailto:fega-norway-support@elixir.no")
    )

    # Add dataset to graph
    g += dataset.to_graph(ds_uri)

    # Link dataset to catalog
    g.add((URIRef(CATALOG_URI), DCAT.dataset, ds_uri))


g.serialize("output/GDI_Norway_data_catalog_2.ttl", format="turtle")

