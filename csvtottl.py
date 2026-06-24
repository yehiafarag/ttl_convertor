import pandas as pd
from rdflib import URIRef, DCAT, DCTERMS
from sempyro import LiteralField
from sempyro.dcat import DCATCatalog, DCATDataset
from sempyro.vcard import VCard

from custom_dcatistribution import CustomDCATDistribution

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
        hasUID=URIRef(f"{BASE}/author/{author_id}"),
    )
    # Add dataset to graph
    g += creator.to_graph(ds_uri)

    # Link dataset to catalog
    g.add((ds_uri,DCTERMS.creator, vcard_uri))


    # 2 Dataset
    dataset = DCATDataset(
        identifier=[ds_id],
        title=[LiteralField(value=str(r["name"]).strip(), language="en")],
        description=[LiteralField(value=str(r["description"]).strip(), language="en")],
        creator=[vcard_uri],
    )

    # Add dataset to graph
    g += dataset.to_graph(ds_uri)

    # Link dataset to catalog
    g.add((URIRef(CATALOG_URI), DCAT.dataset, ds_uri))

    # 3 Distribution
    dist_id = f"{ds_id}-dist"
    dist_uri = URIRef(f"{BASE}/distribution/{dist_id}")

    dist = CustomDCATDistribution (
        title=[LiteralField(value=f"{str(r['name']).strip()} distribution", language="en")],
        description=[LiteralField(value=f"Distribution for {str(r['name']).strip()}", language="en")],
        access_url=URIRef("https://fega-norway.elixir.no/access")
    )

    # Add distribution to graph
    g += dist.to_graph(dist_uri)

    # Link dataset → distribution
    g.add((ds_uri, DCAT.distribution, dist_uri))



g.serialize("output/GDI_Norway_data_catalog_1.ttl", format="turtle")
