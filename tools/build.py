"""Check Weft and build its website.

    python tools/build.py [out-dir]        (default: site/)

1. Checks the ontology (labels, comments, licence) and the examples (domain, range and
   the SHACL shapes). Stops with exit code 1 if anything fails, so nothing broken is
   published.
2. Writes the site GitHub Pages serves at https://rishirajani.github.io/weft/ and
   https://w3id.org/weft redirects to:
     index.html            documentation of the current version
     weft.ttl .jsonld .rdf .nt
     context.jsonld        a JSON-LD context for writing Weft data as plain JSON
     shapes.ttl            the SHACL shapes
     examples/jordan.ttl   the example
     <version>/...         the same files for each version (current and releases/*.ttl)
"""
import html
import json
import shutil
import sys
from collections import Counter
from pathlib import Path

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check import ONTOLOGY, ONTOLOGY_FILE, ROOT, SCHEMA, WEFT, check, class_options, terms_of  # noqa: E402

REPO = "https://github.com/rishirajani/weft"
PAGES = "https://rishirajani.github.io/weft/"
SHAPES_FILE = ROOT / "shapes" / "weft.shacl.ttl"
EXAMPLE_FILE = ROOT / "examples" / "jordan.ttl"
EX = Namespace("https://example.org/jordan#")
USED_BY = [
    ("Graph Resume", "https://rishirajani.github.io/Graph-Resume/",
     "Rishi Rajani's résumé as an interactive knowledge graph, published as Turtle and JSON-LD.",
     "https://rishirajani.github.io/Graph-Resume/resume.ttl"),
]
CONTEXT_PREFIXES = {"weft": str(WEFT), "schema": str(SCHEMA), "skos": str(SKOS), "xsd": str(XSD)}


# ---------------------------------------------------------------- shapes
def run_shapes(data, shapes):
    try:
        from pyshacl import validate
    except ImportError:
        print("pyshacl isn't installed; skipping the SHACL check (pip install pyshacl).")
        return True, []
    conforms, report, text = validate(data, shacl_graph=shapes, ont_graph=None, advanced=True, allow_warnings=True)
    SH = Namespace("http://www.w3.org/ns/shacl#")
    warnings = []
    for r in report.subjects(SH.resultSeverity, SH.Warning):
        node = report.value(r, SH.focusNode)
        warnings.append(f"{data.value(node, SCHEMA.name) or node}: {report.value(r, SH.resultMessage)}")
    if not conforms:
        print(text)
    return conforms, sorted(warnings)


# ---------------------------------------------------------------- JSON-LD context
def context(vocab):
    ctx = {"@version": 1.1, **CONTEXT_PREFIXES}
    for t in sorted(terms_of(vocab)):
        local = t[len(WEFT):]
        if (t, RDF.type, OWL.ObjectProperty) in vocab:
            ctx[local] = {"@id": f"weft:{local}", "@type": "@id"}
        elif (t, RDF.type, OWL.DatatypeProperty) in vocab:
            ctx[local] = {"@id": f"weft:{local}"}
        else:
            ctx[local] = f"weft:{local}"
    # the schema.org terms Weft data uses most, so a plain JSON document reads naturally
    for name in ("name", "description", "startDate", "endDate", "url", "author"):
        ctx[name] = {"@id": f"schema:{name}", **({"@type": "@id"} if name in ("url", "author") else {})}
    for cls in ("Person", "Organization", "CollegeOrUniversity", "OrganizationRole", "EducationalOccupationalCredential",
                "CreativeWork", "ScholarlyArticle", "Language", "DefinedTerm", "DefinedTermSet"):
        ctx[cls] = f"schema:{cls}"
    ctx["exactMatch"] = {"@id": "skos:exactMatch", "@type": "@id"}
    ctx["closeMatch"] = {"@id": "skos:closeMatch", "@type": "@id"}
    ctx["id"] = "@id"
    ctx["type"] = "@type"
    return {"@context": ctx}


# ---------------------------------------------------------------- documentation
def docs(vocab, example, version_dir=None):
    """The documentation page. version_dir is set for the copy inside <version>/."""
    e = html.escape
    up = "../" if version_dir else ""
    lit = lambda s, p: str(vocab.value(s, p) or "")
    names = {s: str(o) for s, o in example.subject_objects(SCHEMA.name)}

    def short(x):
        s = str(x)
        for p, ns in (("weft", str(WEFT)), ("schema", str(SCHEMA)), ("xsd", str(XSD)), ("skos", str(SKOS))):
            if s.startswith(ns):
                return f"{p}:{s[len(ns):]}"
        return s

    def ref(x):
        if isinstance(x, BNode):
            return " or ".join(ref(o) for o in class_options(x, vocab))
        s = str(x)
        if s.startswith(str(WEFT)):
            return f'<a href="#{e(s[len(str(WEFT)):])}"><code>{e(short(x))}</code></a>'
        if s.startswith("http"):
            return f'<a href="{e(s)}"><code>{e(short(x))}</code></a>'
        return f"<code>{e(short(x))}</code>"

    def node(n):
        return f"<span class='n'>{e(names.get(n, short(n)))}</span>"

    usage = Counter(p for p in example.predicates() if str(p).startswith(str(WEFT)))
    class_usage = Counter(o for o in example.objects(None, RDF.type))
    labels = {t: lit(t, RDFS.label) for t in terms_of(vocab)}

    def term_block(t, kind):
        local = str(t)[len(str(WEFT)):]
        rows = [("IRI", f"<code>{e(str(t))}</code>")]
        for p, name in ((RDFS.domain, "From"), (RDFS.range, "To")):
            v = vocab.value(t, p)
            if v is not None:
                rows.append((name, ref(v)))
        for p, name in ((RDFS.subClassOf, "Subclass of"), (RDFS.subPropertyOf, "Narrower than"), (OWL.inverseOf, "Inverse of")):
            vs = list(vocab.objects(t, p))
            if vs:
                rows.append((name, ", ".join(ref(v) for v in vs)))
        narrower = sorted(s for s in vocab.subjects(RDFS.subPropertyOf, t))
        if narrower:
            rows.append(("Broader than", ", ".join(ref(v) for v in narrower)))
        sees = list(vocab.objects(t, RDFS.seeAlso))
        if sees:
            rows.append(("Compare", ", ".join(ref(v) for v in sees)))
        examples = ""
        if kind == "class" and class_usage[t]:
            ex = sorted(example.subjects(RDF.type, t))[:2]
            examples = "<ul class='ex'>" + "".join(f"<li>{node(s)} <span class='rel'>is a</span> {e(labels[t])}</li>" for s in ex) + "</ul>"
        elif kind == "object" and usage[t]:
            ex = sorted(example.subject_objects(t))[:3]
            examples = "<ul class='ex'>" + "".join(f"<li>{node(s)} <span class='rel'>{e(labels[t])}</span> {node(o)}</li>" for s, o in ex) + "</ul>"
        elif kind == "data" and usage[t]:
            s, o = sorted(example.subject_objects(t))[0]
            val = str(o) if len(str(o)) < 90 else str(o)[:88] + "…"
            examples = f"<ul class='ex'><li>{node(s)} <span class='rel'>{e(labels[t])}</span> “{e(val)}”</li></ul>"
        elif kind == "object":
            subs = [s for s in narrower if usage[s]]
            if subs:
                examples = f"<p class='note'>Usually stated through {', '.join(ref(s) for s in subs)}.</p>"
        return f"""<section class="term" id="{e(local)}">
  <h3><a class="anchor" href="#{e(local)}">{e(labels[t])}</a> <code class="curie">weft:{e(local)}</code></h3>
  <p class="def">{e(lit(t, RDFS.comment))}</p>
  <dl>{''.join(f'<dt>{k}</dt><dd>{v}</dd>' for k, v in rows)}</dl>
  {examples}
</section>"""

    order = {s: i for i, s in enumerate(s for s, p, o in vocab.triples((None, RDF.type, None)))}
    pick = lambda kind: sorted((s for s in vocab.subjects(RDF.type, kind) if str(s).startswith(str(WEFT))), key=lambda s: order.get(s, 0))
    classes, objects, datas = pick(OWL.Class), pick(OWL.ObjectProperty), pick(OWL.DatatypeProperty)

    def overview_row(t):
        d, r = vocab.value(t, RDFS.domain), vocab.value(t, RDFS.range)
        return f"<tr><td>{ref(d) if d is not None else '—'}</td><td><a href='#{e(str(t)[len(str(WEFT)):])}'>{e(labels[t])}</a></td><td>{ref(r) if r is not None else '—'}</td></tr>"

    jsonld = vocab.serialize(format="json-ld", context={"weft": str(WEFT), "owl": str(OWL), "rdfs": str(RDFS), "schema": str(SCHEMA), "xsd": str(XSD), "dcterms": str(DCTERMS)}, indent=1)
    version = lit(ONTOLOGY, OWL.versionInfo)
    version_iri = lit(ONTOLOGY, OWL.versionIRI)
    issued = lit(ONTOLOGY, DCTERMS.issued)
    creator = lit(ONTOLOGY, DCTERMS.creator)
    title = lit(ONTOLOGY, DCTERMS.title)
    description = "".join(f"<p>{e(' '.join(par.split()))}</p>" for par in lit(ONTOLOGY, DCTERMS.description).split("\n\n"))
    year = issued[:4]
    used_by = "".join(f'<li><a href="{e(u)}">{e(n)}</a>: {e(d)} <a href="{e(data)}">Data (Turtle)</a></li>' for n, u, d, data in USED_BY)
    this_version = (f'<p class="banner">This is version {e(version)}. <a href="../">The current version</a> may be newer.</p>' if version_dir else "")
    snippet_ttl = """@prefix weft:   <https://w3id.org/weft#> .
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

ex:o-lumen a schema:Organization ; schema:name "Lumen Freight" .
ex:s-sql a schema:DefinedTerm ; schema:name "SQL" ."""
    snippet_json = json.dumps({
        "@context": "https://w3id.org/weft/context.jsonld",
        "id": "https://example.org/jordan#me", "type": "Person", "name": "Jordan Example",
        "worksAs": {"id": "https://example.org/jordan#r-senior", "type": "OrganizationRole", "name": "Senior Data Analyst",
                    "startDate": "2023-03",
                    "at": {"id": "https://example.org/jordan#o-lumen", "type": "Organization", "name": "Lumen Freight"},
                    "used": [{"id": "https://example.org/jordan#s-sql", "type": "DefinedTerm", "name": "SQL"}]},
    }, indent=2, ensure_ascii=False)
    query = """PREFIX weft:   <https://w3id.org/weft#>
PREFIX schema: <https://schema.org/>

# Which roles, projects and courses back each skill?
SELECT ?skill ?evidence WHERE {
  ?x weft:used|weft:trainedIn|weft:shows ?s .
  ?s schema:name ?skill .
  ?x schema:name ?evidence .
} ORDER BY ?skill"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}: a vocabulary for evidence-backed career graphs</title>
<meta name="description" content="Weft is an open OWL vocabulary, built on schema.org, for describing a career as a graph in which every skill links to the roles, projects and courses that show it.">
<link rel="canonical" href="{e(version_iri if version_dir else str(ONTOLOGY))}">
<link rel="alternate" type="text/turtle" href="weft.ttl">
<link rel="alternate" type="application/ld+json" href="weft.jsonld">
<link rel="alternate" type="application/rdf+xml" href="weft.rdf">
<link rel="license" href="https://creativecommons.org/licenses/by/4.0/">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400..800&family=Newsreader:opsz,wght@6..72,300..600&display=swap" rel="stylesheet">
<script type="application/ld+json">
{jsonld}
</script>
<style>
:root {{ --paper:#EEF1F4; --surface:#fff; --ink:#17202D; --ink-2:#3A4456; --muted:#5F687A; --rule:#D3D9E1; --accent:#0D7776;
  --sans:"Schibsted Grotesk",system-ui,sans-serif; --serif:"Newsreader",Georgia,serif; }}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--paper); color:var(--ink); font:16px/1.55 var(--sans) }}
main {{ max-width:880px; margin:0 auto; padding:48px 24px 96px }}
a {{ color:var(--ink); text-underline-offset:3px }}
code {{ font:13.5px/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; background:#E3E8EE; padding:1px 5px; border-radius:4px }}
.weave {{ display:block; width:72px; height:36px; margin:0 0 18px }}
h1 {{ font-size:52px; letter-spacing:-.025em; line-height:1; margin:0 0 8px }}
.sub {{ font:400 22px/1.4 var(--serif); color:var(--ink-2); margin:0 0 28px }}
.lede p {{ font:400 18.5px/1.55 var(--serif); color:var(--ink-2); margin:0 0 12px; max-width:68ch }}
h2 {{ font-size:24px; margin:56px 0 14px; padding-top:12px; border-top:1px solid var(--rule) }}
h2 a {{ text-decoration:none }}
.meta {{ display:grid; grid-template-columns:max-content 1fr; gap:6px 18px; margin:24px 0; font-size:15px }}
.meta dt {{ color:var(--muted) }} .meta dd {{ margin:0; word-break:break-word }}
.downloads a {{ display:inline-block; margin:0 8px 8px 0; padding:6px 14px; border:1px solid var(--rule); border-radius:999px; background:var(--surface); text-decoration:none; font-size:14.5px }}
.downloads a:hover {{ border-color:var(--ink) }}
.banner {{ background:#FFF6CC; border:1px solid #E9D77A; border-radius:10px; padding:10px 14px }}
table {{ width:100%; border-collapse:collapse; font-size:15px; background:var(--surface); border:1px solid var(--rule); border-radius:10px; overflow:hidden }}
th, td {{ text-align:left; padding:8px 12px; border-top:1px solid var(--rule); vertical-align:top }}
th {{ font-size:13px; color:var(--muted); font-weight:600; border-top:0; background:#F6F8FA }}
.term {{ background:var(--surface); border:1px solid var(--rule); border-radius:12px; padding:18px 20px 14px; margin:14px 0; scroll-margin-top:16px }}
.term:target {{ outline:3px solid #F6DE3D; outline-offset:2px }}
.term h3 {{ margin:0; font-size:20px; display:flex; gap:10px; align-items:baseline; flex-wrap:wrap }}
.term h3 .anchor {{ text-decoration:none }}
.curie {{ font-size:13px }}
.def {{ font:400 17px/1.5 var(--serif); color:var(--ink-2); margin:8px 0 12px }}
.term dl {{ display:grid; grid-template-columns:120px 1fr; gap:4px 14px; margin:0; font-size:14.5px }}
.term dt {{ color:var(--muted) }} .term dd {{ margin:0; word-break:break-word }}
.ex {{ margin:10px 0 0; padding:10px 14px; list-style:none; background:#F6F8FA; border-radius:8px; font-size:14.5px }}
.ex li {{ margin:2px 0 }} .ex .rel {{ color:var(--muted); font-style:italic; margin:0 4px }}
.note {{ margin:10px 0 0; font-size:14.5px; color:var(--muted) }}
.related {{ display:grid; gap:12px }}
.related div {{ background:var(--surface); border:1px solid var(--rule); border-radius:12px; padding:14px 18px }}
.related h3 {{ margin:0 0 4px; font-size:17px }}
.related p {{ margin:0; font-size:15px; color:var(--ink-2) }}
pre {{ background:var(--surface); border:1px solid var(--rule); border-radius:10px; padding:14px 16px; overflow:auto; font-size:13px }}
pre code {{ background:none; padding:0 }}
ul.plain {{ padding-left:20px }}
footer {{ margin-top:64px; color:var(--muted); font-size:14px }}
@media (max-width:640px) {{ h1 {{ font-size:38px }} .term dl, .meta {{ grid-template-columns:1fr }} .term dt, .meta dt {{ margin-top:6px }} }}
</style>
</head>
<body>
<main>
{this_version}
<svg class="weave" viewBox="0 0 72 36" aria-hidden="true">
  <g stroke="#17202D" stroke-width="3" stroke-linecap="round" fill="none">
    <path d="M10 3v30M26 3v30M42 3v30M58 3v30" opacity=".35"/>
  </g>
  <path d="M3 12 C 10 7, 10 7, 18 12 S 26 17, 34 12 S 42 7, 50 12 S 58 17, 69 12" stroke="#0D7776" stroke-width="3.2" fill="none" stroke-linecap="round"/>
  <path d="M3 24 C 10 29, 10 29, 18 24 S 26 19, 34 24 S 42 29, 50 24 S 58 19, 69 24" stroke="#A1275D" stroke-width="3.2" fill="none" stroke-linecap="round"/>
</svg>
<h1>{e(title)}</h1>
<p class="sub">A vocabulary for evidence-backed career graphs.</p>
<div class="lede">{description}
<p>The name comes from weaving: the warp is the timeline of roles, studies and projects, and the weft is the skills threaded through them.</p></div>
<dl class="meta">
  <dt>IRI</dt><dd><code>{e(str(ONTOLOGY))}</code></dd>
  <dt>This version</dt><dd><code>{e(version_iri)}</code> (version {e(version)}, published {e(issued)})</dd>
  <dt>Namespace</dt><dd><code>{e(str(WEFT))}</code>, prefix <code>weft:</code></dd>
  <dt>Author</dt><dd>{e(creator)}</dd>
  <dt>Licence</dt><dd><a href="https://creativecommons.org/licenses/by/4.0/" rel="license">CC BY 4.0</a>: free to use and adapt, including commercially, with credit. Data you describe with Weft is yours.</dd>
  <dt>Terms</dt><dd>{len(classes)} classes, {len(objects)} relations, {len(datas)} value properties</dd>
  <dt>Source</dt><dd><a href="{REPO}">{REPO.replace('https://', '')}</a> · <a href="{REPO}/blob/main/CHANGELOG.md">Changes</a> · <a href="{REPO}/issues">Suggest a change</a></dd>
</dl>
<p class="downloads"><a href="weft.ttl">Turtle</a><a href="weft.jsonld">JSON-LD</a><a href="weft.rdf">RDF/XML</a><a href="weft.nt">N-Triples</a><a href="{up}context.jsonld">JSON-LD context</a><a href="{up}shapes.ttl">SHACL shapes</a><a href="{up}examples/jordan.ttl">Example</a></p>

<h2 id="design"><a href="#design">How it fits together</a></h2>
<div class="lede">
<p>The kinds of things come from <a href="https://schema.org/">schema.org</a>: the person is a <code>schema:Person</code>, each job a <code>schema:OrganizationRole</code>, each degree or certificate a <code>schema:EducationalOccupationalCredential</code>, each project a <code>schema:CreativeWork</code>, each skill a <code>schema:DefinedTerm</code>, grouped into skill areas (<code>schema:DefinedTermSet</code>). Only awards and career breaks needed classes of their own.</p>
<p>The relations are Weft's. schema.org mostly links a person straight to an organisation (<code>schema:worksFor</code>, <code>schema:alumniOf</code>) and lists skills on the person as text. In Weft every job, degree and project is its own node, linked to where it happened and to the skills it <a href="#used">used</a>, <a href="#trainedIn">trained</a> or <a href="#shows">certified</a>. That's the evidence layer: any skill can be traced back to the work behind it, and a skill nothing points to stands out.</p>
<p>Where a Weft relation is a special case of a schema.org property it says so (<code>rdfs:subPropertyOf</code>, <code>owl:inverseOf</code>), so data stays useful to tools that only know schema.org. Skills, languages and tools can be matched to shared concepts in <a href="https://esco.ec.europa.eu/">ESCO</a> or <a href="https://www.wikidata.org/">Wikidata</a> with <code>skos:exactMatch</code> and <code>skos:closeMatch</code>.</p>
</div>

<h2 id="start"><a href="#start">Using it</a></h2>
<p>In Turtle, declare the prefix and describe the career with schema.org types and Weft relations:</p>
<pre><code>{e(snippet_ttl)}</code></pre>
<p>As JSON-LD, the <a href="{up}context.jsonld">context</a> lets you write the same thing as plain JSON:</p>
<pre><code>{e(snippet_json)}</code></pre>
<p>Then ask the graph questions, for example in SPARQL:</p>
<pre><code>{e(query)}</code></pre>
<p>To check data, run <a href="{REPO}/blob/main/tools/check.py"><code>tools/check.py</code></a> from the repository (every relation connects the kinds of things it should) and validate it against the <a href="{up}shapes.ttl">SHACL shapes</a>, which also warn about skills nothing backs up.</p>

<h2 id="overview"><a href="#overview">All relations at a glance</a></h2>
<table><thead><tr><th>From</th><th>Relation</th><th>To</th></tr></thead><tbody>
{''.join(overview_row(t) for t in objects)}
</tbody></table>

<h2 id="classes"><a href="#classes">Classes</a></h2>
{''.join(term_block(t, 'class') for t in classes)}

<h2 id="relations"><a href="#relations">Relations</a></h2>
<p>Examples are from <a href="{up}examples/jordan.ttl">the example</a>, a made-up person.</p>
{''.join(term_block(t, 'object') for t in objects)}

<h2 id="values"><a href="#values">Value properties</a></h2>
{''.join(term_block(t, 'data') for t in datas)}

<h2 id="related"><a href="#related">Related vocabularies</a></h2>
<p>Weft reuses or links to these rather than replacing them.</p>
<div class="related">
<div><h3><a href="https://schema.org/">schema.org</a></h3><p>Weft's base: all of its classes except two are schema.org's, and several relations are declared as special cases of schema.org properties. schema.org can say a person has skills or worked for an organisation, but not which role or project a skill came from.</p></div>
<div><h3><a href="https://esco.ec.europa.eu/">ESCO</a> and <a href="https://www.wikidata.org/">Wikidata</a></h3><p>Shared concepts to map skills, occupations, languages and tools to. ESCO is the EU's multilingual classification of skills, competences and occupations. Weft describes a person's evidence; these say what the skill is.</p></div>
<div><h3><a href="https://europass.europa.eu/en/european-learning-model">European Learning Model</a></h3><p>The European Commission's ontology behind Europass and European Digital Credentials: qualifications, learning outcomes and signed credentials issued by institutions. It covers the issuer's side of learning; Weft covers a person's own account across work and study, and a Weft credential can link to a European Digital Credential.</p></div>
<div><h3><a href="https://www.w3.org/wiki/ResumeRDFOntology">ResumeRDF</a></h3><p>An early RDF vocabulary for CVs (Bojārs and Breslin, 2007), modelling the CV as a document with work-history, education and skill entries. It hasn't been updated in many years. Weft models the career rather than the document, and ties skills to evidence.</p></div>
<div><h3><a href="https://jsonresume.org/">JSON Resume</a> and <a href="https://www.hropenstandards.org/">HR Open Standards</a></h3><p>JSON schemas for CV and recruiting data: JSON Resume for rendering a CV from one file, HR Open (formerly HR-XML) for exchanging candidate and job data between HR systems. Neither is linked data, and skills are lists rather than links to the work that shows them.</p></div>
<div><h3>Commercial skills catalogues</h3><p>Skills taxonomies from vendors such as Lightcast, LinkedIn, Workday and Textkernel describe which skills exist and how they relate, mostly under their own licences. Weft data can map to any of them with SKOS.</p></div>
</div>

<h2 id="used-by"><a href="#used-by">Used by</a></h2>
<ul class="plain">{used_by}</ul>
<p>Using Weft somewhere? <a href="{REPO}/issues">Open an issue</a> to be listed.</p>

<h2 id="cite"><a href="#cite">Citing</a></h2>
<p>{e(creator)} ({e(year)}). <em>Weft: a vocabulary for evidence-backed career graphs</em>, version {e(version)}. <code>{e(version_iri)}</code></p>

<footer>Generated from <a href="weft.ttl">weft.ttl</a>. Term IRIs such as <code>{e(str(WEFT))}used</code> open their section on this page.<br>
{e(lit(ONTOLOGY, DCTERMS.rights))}</footer>
</main>
</body>
</html>
"""


# ---------------------------------------------------------------- build
def write_version(out, vocab, ttl_text, example, version_dir=None):
    out.mkdir(parents=True, exist_ok=True)
    (out / "weft.ttl").write_text(ttl_text)
    ctx = {"weft": str(WEFT), "owl": str(OWL), "rdfs": str(RDFS), "schema": str(SCHEMA), "xsd": str(XSD),
           "dcterms": str(DCTERMS), "skos": str(SKOS), "vann": "http://purl.org/vocab/vann/"}
    (out / "weft.jsonld").write_text(vocab.serialize(format="json-ld", context=ctx, indent=1))
    (out / "weft.rdf").write_text(vocab.serialize(format="xml"))
    (out / "weft.nt").write_text(vocab.serialize(format="nt"))
    (out / "index.html").write_text(docs(vocab, example, version_dir))


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "site"
    from rdflib import Graph
    vocab = Graph().parse(ONTOLOGY_FILE, format="turtle")
    example = Graph().parse(EXAMPLE_FILE, format="turtle")
    shapes = Graph().parse(SHAPES_FILE, format="turtle")

    errors = check(vocab, [EXAMPLE_FILE])
    unused = sorted(t[len(WEFT):] for t in terms_of(vocab)
                    if (None, t, None) not in example and (None, RDF.type, t) not in example and t != WEFT.heldRole)
    if unused:
        errors.append("The example doesn't use: " + ", ".join(unused))
    if errors:
        print("Weft check failed:")
        print("\n".join("  - " + x for x in errors))
        sys.exit(1)
    conforms, warnings = run_shapes(example, shapes)
    if not conforms:
        print("The example doesn't conform to the shapes.")
        sys.exit(1)
    if warnings:
        print("Shape warnings on the example (fix them; the example should be clean):")
        print("\n".join("  - " + w for w in warnings))
        sys.exit(1)

    if out.exists():
        shutil.rmtree(out)
    version = str(vocab.value(ONTOLOGY, OWL.versionInfo))
    ttl = ONTOLOGY_FILE.read_text()
    write_version(out, vocab, ttl, example)
    write_version(out / version, vocab, ttl, example, version_dir=version)
    for old in sorted((ROOT / "releases").glob("*.ttl")):
        if old.stem == version:
            continue
        g = Graph().parse(old, format="turtle")
        write_version(out / old.stem, g, old.read_text(), example, version_dir=old.stem)
    (out / "context.jsonld").write_text(json.dumps(context(vocab), indent=1) + "\n")
    shutil.copy(SHAPES_FILE, out / "shapes.ttl")
    (out / "examples").mkdir()
    shutil.copy(EXAMPLE_FILE, out / "examples" / "jordan.ttl")
    (out / ".nojekyll").write_text("")
    print(f"Weft {version}: {len(terms_of(vocab))} terms checked; the example uses all of them and passes the shapes. "
          f"Site written to {out}.")


if __name__ == "__main__":
    main()
