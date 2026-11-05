"""Check that RDF data uses Weft correctly.

    python tools/check.py data.ttl [more.ttl ...] [--ontology path/to/weft.ttl]

Every weft: term the data uses must exist, and each relation must connect the kinds of
things its domain and range say (schema.org classes, with the few subclass links that
matter here). The ontology itself must give every term a label and a comment.
Exits 1 and lists the problems if anything is wrong.
"""
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS

ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_FILE = ROOT / "ontology" / "weft.ttl"
WEFT = Namespace("https://w3id.org/weft#")
ONTOLOGY = URIRef("https://w3id.org/weft")
SCHEMA = Namespace("https://schema.org/")

# The part of the schema.org class hierarchy the checks need (schema.org itself isn't loaded).
SUPER = {
    SCHEMA.CollegeOrUniversity: SCHEMA.EducationalOrganization,
    SCHEMA.HighSchool: SCHEMA.EducationalOrganization,
    SCHEMA.School: SCHEMA.EducationalOrganization,
    SCHEMA.EducationalOrganization: SCHEMA.Organization,
    SCHEMA.Corporation: SCHEMA.Organization,
    SCHEMA.NGO: SCHEMA.Organization,
    SCHEMA.GovernmentOrganization: SCHEMA.Organization,
    SCHEMA.ResearchOrganization: SCHEMA.Organization,
    SCHEMA.EmployeeRole: SCHEMA.OrganizationRole,
    SCHEMA.ScholarlyArticle: SCHEMA.Article,
    SCHEMA.Article: SCHEMA.CreativeWork,
    SCHEMA.SoftwareSourceCode: SCHEMA.CreativeWork,
    SCHEMA.SoftwareApplication: SCHEMA.CreativeWork,
    SCHEMA.Dataset: SCHEMA.CreativeWork,
    SCHEMA.Thesis: SCHEMA.CreativeWork,
    SCHEMA.Report: SCHEMA.Article,
    SCHEMA.CategoryCode: SCHEMA.DefinedTerm,
    SCHEMA.CategoryCodeSet: SCHEMA.DefinedTermSet,
}


def load_ontology(path=ONTOLOGY_FILE):
    return Graph().parse(path, format="turtle")


def ancestors(c, vocab):
    seen, todo = set(), [c]
    while todo:
        x = todo.pop()
        if x in seen:
            continue
        seen.add(x)
        if x in SUPER:
            todo.append(SUPER[x])
        todo.extend(o for o in vocab.objects(x, RDFS.subClassOf) if isinstance(o, URIRef))
    return seen


def class_options(node, vocab):
    """A class, or the members of an owl:unionOf."""
    if node is None:
        return None
    u = vocab.value(node, OWL.unionOf)
    return list(Collection(vocab, u)) if u is not None else [node]


def terms_of(vocab):
    return {s for s in vocab.subjects(RDF.type, None) if isinstance(s, URIRef) and str(s).startswith(str(WEFT))}


def check_ontology(vocab):
    errors = []
    if vocab.value(ONTOLOGY, DCTERMS.license) is None:
        errors.append("The ontology has no dcterms:license.")
    if vocab.value(ONTOLOGY, OWL.versionIRI) is None:
        errors.append("The ontology has no owl:versionIRI.")
    for t in sorted(terms_of(vocab)):
        for p, what in ((RDFS.label, "label"), (RDFS.comment, "comment")):
            if vocab.value(t, p) is None:
                errors.append(f"weft:{t[len(WEFT):]} has no {what}.")
        if vocab.value(t, RDFS.isDefinedBy) != ONTOLOGY:
            errors.append(f"weft:{t[len(WEFT):]} has no rdfs:isDefinedBy <{ONTOLOGY}>.")
    return errors


def check_data(vocab, g, name="data"):
    """Domain, range and existence checks for one graph."""
    def short(x):
        q = g.namespace_manager.normalizeUri(x) if isinstance(x, URIRef) else str(x)
        return q if not q.startswith("<") else str(x)

    errors = []
    terms = terms_of(vocab)
    types = defaultdict(set)
    for s, o in g.subject_objects(RDF.type):
        types[s] |= ancestors(o, vocab)
    for c in set(g.objects(None, RDF.type)):
        if str(c).startswith(str(WEFT)) and c not in terms:
            errors.append(f"{name}: class {short(c)} isn't defined in Weft.")
    for s, p, o in sorted(g):
        if not str(p).startswith(str(WEFT)):
            continue
        if p not in terms:
            errors.append(f"{name}: {short(p)} isn't defined in Weft.")
            continue
        is_object = (p, RDF.type, OWL.ObjectProperty) in vocab
        if is_object != isinstance(o, URIRef):
            errors.append(f"{name}: {short(s)} {short(p)} should point to {'an item' if is_object else 'a value'}.")
            continue
        dom = class_options(vocab.value(p, RDFS.domain), vocab)
        if dom and not types[s] & set(dom):
            errors.append(f"{name}: {short(s)} {short(p)} …: the subject isn't a {' or '.join(short(d) for d in dom)}.")
        rng = class_options(vocab.value(p, RDFS.range), vocab)
        if is_object and rng and not types[o] & set(rng):
            errors.append(f"{name}: … {short(p)} {short(o)}: the target isn't a {' or '.join(short(r) for r in rng)}.")
    return errors


def check(vocab, data_paths):
    errors = check_ontology(vocab)
    for path in data_paths:
        path = Path(path)
        errors += check_data(vocab, Graph().parse(path, format="turtle"), path.name)
    return errors


def main(argv):
    ontology = ONTOLOGY_FILE
    if "--ontology" in argv:
        i = argv.index("--ontology")
        ontology = Path(argv[i + 1])
        argv = argv[:i] + argv[i + 2:]
    if not argv:
        print(__doc__)
        return 2
    vocab = load_ontology(ontology)
    errors = check(vocab, argv)
    if errors:
        print("The data doesn't match Weft:")
        print("\n".join("  - " + x for x in errors))
        return 1
    print(f"Weft {vocab.value(ONTOLOGY, OWL.versionInfo)}: {len(terms_of(vocab))} terms; "
          f"{', '.join(Path(p).name for p in argv)} use{'s' if len(argv) == 1 else ''} them correctly.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
