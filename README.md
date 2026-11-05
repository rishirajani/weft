# Weft

**A vocabulary for evidence-backed career graphs.**

Weft is a small, open OWL vocabulary for describing a career as a graph: the roles a person
held, what they studied, built and wrote, the credentials and awards they received, and the
skills each of those involved. Every role, degree and project is its own node, linked to where
it happened and to the skills it used, taught or certified, so any skill can be traced back to
the work behind it.

It builds on [schema.org](https://schema.org/) for the kinds of things and adds the relations
schema.org doesn't have. Skills can be matched to [ESCO](https://esco.ec.europa.eu/) or
[Wikidata](https://www.wikidata.org/) with SKOS.

- **Documentation:** <https://rishirajani.github.io/weft/> (permanent IRI
  `https://w3id.org/weft`, once the w3id.org registration is merged)
- **Namespace:** `https://w3id.org/weft#`, prefix `weft:`
- **Version:** 1.0 (`https://w3id.org/weft/1.0`), see the [changelog](CHANGELOG.md)
- **Licence:** [CC BY 4.0](LICENSE). Data you describe with Weft is yours.

The name comes from weaving: the warp is the timeline of roles, studies and projects, and the
weft is the skills threaded through them.

## A taste

```turtle
@prefix weft:   <https://w3id.org/weft#> .
@prefix schema: <https://schema.org/> .
@prefix ex:     <https://example.org/jordan#> .

ex:me a schema:Person ;
  schema:name "Jordan Example" ;
  weft:worksAs ex:r-senior .

ex:r-senior a schema:OrganizationRole ;
  schema:name "Senior Data Analyst" ;
  schema:startDate "2023-03" ;
  weft:at ex:o-lumen ;
  weft:used ex:s-sql .
```

The full [example](examples/jordan.ttl) is a made-up person that uses every term.

## What's here

| Path | |
| --- | --- |
| [`ontology/weft.ttl`](ontology/weft.ttl) | The ontology: 2 classes, 22 relations, 4 value properties. |
| [`shapes/weft.shacl.ttl`](shapes/weft.shacl.ttl) | SHACL shapes for Weft data, including a warning for skills nothing backs up. |
| [`examples/jordan.ttl`](examples/jordan.ttl) | The example. |
| [`tools/check.py`](tools/check.py) | Checks that data uses Weft's terms with the right domains and ranges. |
| [`tools/build.py`](tools/build.py) | Runs all checks and builds the website (documentation, Turtle, JSON-LD, RDF/XML, N-Triples, JSON-LD context). |
| [`releases/`](releases/) | Earlier versions, kept so their version IRIs keep resolving. |
| [`w3id/`](w3id/) | The redirect rules for w3id.org and how to register them. |

## Checking your own data

```sh
pip install rdflib pyshacl
python tools/check.py my-career.ttl
python -m pyshacl -s shapes/weft.shacl.ttl my-career.ttl
```

## Building the site

```sh
python tools/build.py site    # checks everything, then writes site/
```

On every push to `main`, the [workflow](.github/workflows/pages.yml) runs the same build and
publishes `site/` to GitHub Pages. If a check fails, nothing is published.

## Used by

- [Graph Resume](https://rishirajani.github.io/Graph-Resume/), Rishi Rajani's résumé as an
  interactive knowledge graph ([data](https://rishirajani.github.io/Graph-Resume/resume.ttl)).

Using Weft? Open an issue to be listed, or to suggest a change to the vocabulary.

## Citing

Rishi Rajani (2026). *Weft: a vocabulary for evidence-backed career graphs*, version 1.0.
https://w3id.org/weft/1.0
