import requests
import xml.etree.ElementTree as ET
import time

import sqlite3

ESEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

def get_ids(year):
    """return the IDs of fibromylgia papers piblishe in a given year"""
    params = {
        "db": "pubmed",
        "term": f"fibromyalgia AND {year}[pdat]",
        "retmode": "json",
        "retmax": "9999"
    }

    response = requests.get(ESEARCH_URL, params = params)
    time.sleep(0.4)
    data = response.json()

    return data["esearchresult"]["idlist"]

def fetch_papers(ids):
    """retrieve information about a paper given its ID"""
    params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml"
    }

    response = requests.get(FETCH_URL, params = params)
    time.sleep(0.4)
    root = ET.fromstring(response.text)

    papers = []
    for article in root.findall("PubmedArticle"):
        pmid = article.findtext("MedlineCitation/PMID")

        title_el = article.find("MedlineCitation/Article/ArticleTitle")
        title = "".join(title_el.itertext()) if title_el is not None else ""

        abstract = " ".join(
            "".join(p.itertext())
            for p in article.findall("MedlineCitation/Article/Abstract/AbstractText")
        )

        date = "MedlineCitation/Article/Journal/JournalIssue/PubDate/"
        year_text = article.findtext(date + "Year") or (article.findtext(date + "MedlineDate") or "")[:4]
        year = int(year_text) if year_text.isdigit() else None

        pub_types = [pt.text for pt in article.findall("MedlineCitation/Article/PublicationTypeList/PublicationType")]
        mesh = [d.text for d in article.findall("MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName")]

        papers.append({
            "pmid": pmid, "title": title, "abstract": abstract,
            "year": year, "pub_types": pub_types, "mesh": mesh,
        })
    return papers

def setup_database(conn):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS papers (
        pmid     TEXT PRIMARY KEY,
        title    TEXT,
        abstract TEXT,
        year     INTEGER
    )
""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS publication_types (
        pmid     TEXT,
        pub_type TEXT,
        PRIMARY KEY (pmid, pub_type)
    )
""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS mesh_terms (
        pmid TEXT,
        term TEXT,
        PRIMARY KEY (pmid, term)
    )
""")

def main():
    conn = sqlite3.connect("data/fibro.db")
    setup_database(conn)
    for year in range(1970, 2027):
        ids = get_ids(year)
        print(f"{year}: {len(ids)} papers")

        for start in range(0, len(ids), 200):
            batch = ids[start:start + 200]
            papers = fetch_papers(batch)

            conn.executemany(
                "INSERT OR IGNORE INTO papers (pmid, title, abstract, year) VALUES (:pmid, :title, :abstract, :year)",
                papers
            )

            type_rows = [(p["pmid"], t) for p in papers for t in p["pub_types"]]
            conn.executemany("INSERT OR IGNORE INTO publication_types VALUES (?, ?)", type_rows)

            mesh_rows = [(p["pmid"], m) for p in papers for m in p["mesh"]]
            conn.executemany("INSERT OR IGNORE INTO mesh_terms VALUES (?, ?)", mesh_rows)
            
            conn.commit()

if __name__ == "__main__":
    main()