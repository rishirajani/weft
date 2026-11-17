# Competency questions

What Weft is for, written as the questions a graph described with Weft should be able to answer.
Each question comes with a SPARQL query and its answer on the [example](examples/jordan.ttl), so
you can check the vocabulary against them, or run them on your own data.

The queries use these prefixes:

```sparql
PREFIX weft:   <https://w3id.org/weft#>
PREFIX schema: <https://schema.org/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
```

Put the prefixes in front of a query and run it in any SPARQL tool, or in Python with
[rdflib](https://rdflib.readthedocs.io/):

```python
import rdflib

PREFIXES = """
PREFIX weft:   <https://w3id.org/weft#>
PREFIX schema: <https://schema.org/>
PREFIX skos:   <http://www.w3.org/2004/02/skos/core#>
"""
query = """
SELECT ?language ?level WHERE {
  ?p weft:speaks ?l . ?l schema:name ?language .
  OPTIONAL { ?l weft:proficiency ?level }
}
"""
g = rdflib.Graph().parse("examples/jordan.ttl")
for row in g.query(PREFIXES + query):
    print(row)
```

Two notes that apply throughout:

- The queries assume a graph describes one person, which is how Weft is used today. For a graph
  with several people, add `?p a schema:Person` and pick the person.
- Dates are plain text in `YYYY` or `YYYY-MM` form (the SHACL shapes enforce this), so they sort
  correctly as text.

## Roles and career path

### 1. What roles does the person hold now, and which have ended?

Terms: `worksAs`, `workedAs`, `at`

```sparql
SELECT ?roleName ?org ?status ?start ?end WHERE {
  { ?p weft:worksAs ?role . BIND("current" AS ?status) }
  UNION
  { ?p weft:workedAs ?role . BIND("ended" AS ?status) }
  ?role schema:name ?roleName .
  OPTIONAL { ?role weft:at/schema:name ?org }
  OPTIONAL { ?role schema:startDate ?start }
  OPTIONAL { ?role schema:endDate ?end }
} ORDER BY DESC(?start)
```

On the example: Senior Data Analyst at Lumen Freight (current, since 2023-03); Data Analyst at Lumen Freight (ended, 2020-09 to 2023-02).

### 2. Where was each role held?

Terms: `heldRole`, `workedAs`, `worksAs`, `at`

```sparql
SELECT ?roleName ?orgName WHERE {
  ?p weft:heldRole|weft:workedAs|weft:worksAs ?role .
  ?role schema:name ?roleName ; weft:at/schema:name ?orgName .
}
```

On the example: Both roles at Lumen Freight.

### 3. Which roles came from a promotion, and from which earlier role?

Terms: `promotedFrom`

```sparql
SELECT ?roleName ?fromName ?orgName WHERE {
  ?role weft:promotedFrom ?from .
  ?role schema:name ?roleName . ?from schema:name ?fromName .
  OPTIONAL { ?role weft:at/schema:name ?orgName }
}
```

On the example: Senior Data Analyst, promoted from Data Analyst, at Lumen Freight.

### 4. Which programme of study led directly to a role?

Terms: `ledTo`

```sparql
SELECT ?studyName ?roleName WHERE {
  ?study weft:ledTo ?role .
  ?study schema:name ?studyName . ?role schema:name ?roleName .
}
```

On the example: The Analytics Engineering Certificate led to the Data Analyst role.

### 5. What happened during a gap between roles?

Terms: `took`, `included`

```sparql
SELECT ?breakName ?start ?end ?whatName WHERE {
  ?p weft:took ?brk .
  ?brk schema:name ?breakName .
  OPTIONAL { ?brk schema:startDate ?start }
  OPTIONAL { ?brk schema:endDate ?end }
  OPTIONAL { ?brk weft:included/schema:name ?whatName }
}
```

On the example: A gap year (2015-09 to 2016-09) that included a volunteer food bank stock tracker and the Cloud Data Practitioner certification.

## Education and credentials

### 6. Which degrees or certificates did the person study, and which do they hold?

Terms: `studied`, `holds`, `at`

```sparql
SELECT ?name ?schoolName (IF(BOUND(?held), "holds", "studied") AS ?status) WHERE {
  { ?p weft:studied ?c } UNION { ?p weft:holds ?c }
  ?c schema:name ?name .
  OPTIONAL { ?c weft:at/schema:name ?schoolName }
  OPTIONAL { ?p weft:holds ?c . BIND(true AS ?held) }
}
```

On the example: Studied: B.Sc. Statistics and the Analytics Engineering Certificate. Holds: Cloud Data Practitioner. Studying something doesn't claim it was finished or awarded; only `holds` does.

### 7. Which organisations co-ran a programme with the school?

Terms: `runWith`

```sparql
SELECT ?programme ?school ?partner WHERE {
  ?c weft:runWith ?o ; schema:name ?programme .
  ?o schema:name ?partner .
  OPTIONAL { ?c weft:at/schema:name ?school }
}
```

On the example: The Analytics Engineering Certificate, run by Example Data Academy with Lumen Freight.

### 8. Which projects were done as part of a degree?

Terms: `partOf`

```sparql
SELECT ?projectName ?degreeName WHERE {
  ?project weft:partOf ?degree .
  ?degree a schema:EducationalOccupationalCredential .
  ?project schema:name ?projectName . ?degree schema:name ?degreeName .
}
```

On the example: The bachelor's thesis on forecasting weekly parcel volumes, part of the B.Sc. Statistics.

## Skills and the evidence behind them

### 9. Which roles, projects, breaks or awards show the person using each skill?

Terms: `used`

```sparql
SELECT ?skillName (GROUP_CONCAT(DISTINCT ?whereName; separator=", ") AS ?usedIn) WHERE {
  ?where weft:used ?skill .
  ?skill schema:name ?skillName . ?where schema:name ?whereName .
} GROUP BY ?skillName ORDER BY ?skillName
```

On the example: Six skills, for example SQL in both roles and the delivery delay dashboard, and dbt in the senior role, the dashboard and the team award.

### 10. Which skills were only taught, never used in work or projects?

Terms: `trainedIn`, `used`

```sparql
SELECT DISTINCT ?skillName ?courseName WHERE {
  ?course weft:trainedIn ?skill .
  ?skill schema:name ?skillName . ?course schema:name ?courseName .
  FILTER NOT EXISTS { ?anything weft:used ?skill }
} ORDER BY ?skillName
```

On the example: None: every skill taught in the example is also used somewhere. On a real graph, this finds skills that rest on coursework alone.

### 11. Which certifications are evidence of which skills?

Terms: `shows`

```sparql
SELECT ?certName ?skillName WHERE {
  ?cert weft:shows ?skill .
  ?cert schema:name ?certName . ?skill schema:name ?skillName .
}
```

On the example: Cloud Data Practitioner is evidence of SQL.

### 12. Which skills have no evidence at all?

Terms: `inGroup`, `used`, `trainedIn`, `shows`

```sparql
SELECT ?skillName WHERE {
  ?skill weft:inGroup ?area ; schema:name ?skillName .
  FILTER NOT EXISTS { ?x weft:used|weft:trainedIn|weft:shows ?skill }
} ORDER BY ?skillName
```

On the example: None, and that's the expected answer. The SHACL shapes warn about any skill that appears here.

### 13. Which skill areas does the person focus on, and which skills fall under each?

Terms: `focusOn`, `inGroup`

```sparql
SELECT ?areaName (COUNT(?skill) AS ?skills) (GROUP_CONCAT(?skillName; separator=", ") AS ?list) WHERE {
  ?p weft:focusOn ?area . ?area schema:name ?areaName .
  OPTIONAL { ?skill weft:inGroup ?area ; schema:name ?skillName }
} GROUP BY ?areaName ORDER BY DESC(?skills)
```

On the example: Data engineering (SQL, dbt, Python, Spreadsheets) and Statistics (Statistical modelling).

### 14. When did the person first use each skill, and in how many roles or projects?

Terms: `used`, `schema:startDate`

```sparql
SELECT ?skillName (MIN(STR(?start)) AS ?firstUsed) (COUNT(DISTINCT ?where) AS ?places) WHERE {
  ?where weft:used ?skill ; schema:startDate ?start .
  ?skill schema:name ?skillName .
} GROUP BY ?skillName ORDER BY ?firstUsed
```

On the example: Spreadsheets first, from 2015-09; dbt last, from 2023-03, in three places. Only items with a start date count.

### 15. Which skills match a Wikidata or ESCO concept?

Terms: `inGroup`, `skos:exactMatch`, `skos:closeMatch`

```sparql
SELECT ?skillName ?match ?how WHERE {
  ?skill weft:inGroup ?area ; schema:name ?skillName .
  { ?skill skos:exactMatch ?match . BIND("exact" AS ?how) }
  UNION
  { ?skill skos:closeMatch ?match . BIND("close" AS ?how) }
} ORDER BY ?skillName
```

On the example: Python and SQL match Wikidata exactly; Statistical modelling is a close match.

## Languages, awards and work

### 16. Which languages does the person speak, and at what level?

Terms: `speaks`, `proficiency`

```sparql
SELECT ?language ?level WHERE {
  ?p weft:speaks ?l . ?l schema:name ?language .
  OPTIONAL { ?l weft:proficiency ?level }
}
```

On the example: English (Native) and German (B2).

### 17. Which awards came from which organisation, and for which skills?

Terms: `received`, `awardedBy`, `used`

```sparql
SELECT ?awardName ?orgName (GROUP_CONCAT(?skillName; separator=", ") AS ?skills) WHERE {
  ?p weft:received ?award . ?award schema:name ?awardName .
  OPTIONAL { ?award weft:awardedBy/schema:name ?orgName }
  OPTIONAL { ?award weft:used/schema:name ?skillName }
} GROUP BY ?awardName ?orgName
```

On the example: The team award for the depot analytics rollout, from Lumen Freight, for dbt.

### 18. What did the person build or write?

Terms: `built`, `wrote`

```sparql
SELECT ?what ?kind ?start WHERE {
  { ?p weft:built ?w . BIND("built" AS ?kind) } UNION { ?p weft:wrote ?w . BIND("wrote" AS ?kind) }
  ?w schema:name ?what .
  OPTIONAL { ?w schema:startDate ?start }
} ORDER BY DESC(?start)
```

On the example: Built the delivery delay dashboard (2023-05); wrote a short note on seasonal parcel forecasts (2021-03).

## Questions Weft doesn't answer

These are left out on purpose, and they mark the edges of the vocabulary. Weft adds a term only
when real data needs it.

- **How good is the person at a skill?** Weft records evidence that a skill was used, taught or
  certified, not a self-rated level. Only languages have a level (`weft:proficiency`).
- **Who can vouch for a claim?** References and referees aren't described.
- **Pay, team size and reporting lines.** Not part of a career graph as Weft sees it.
- **When within a role was a skill used?** `weft:used` links a skill to the whole role, project,
  break or award, not to a period inside it.

If you need one of these, [open an issue](https://github.com/rishirajani/weft/issues) and describe
the data you have.
