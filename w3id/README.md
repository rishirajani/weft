# Registering https://w3id.org/weft

[w3id.org](https://w3id.org/) gives Weft permanent IRIs that redirect to wherever the files
are hosted (now GitHub Pages). If the hosting ever moves, only the redirect changes and every
Weft term keeps working.

The redirect rules are in [`ids/weft/.htaccess`](ids/weft/.htaccess), ready to copy into the
w3id.org repository. They send:

| Request | Goes to |
| --- | --- |
| `https://w3id.org/weft` (browser) | the documentation, `https://rishirajani.github.io/weft/` |
| `https://w3id.org/weft` (`Accept: text/turtle`, JSON-LD, RDF/XML, N-Triples) | `weft.ttl`, `weft.jsonld`, `weft.rdf`, `weft.nt` |
| `https://w3id.org/weft/1.0` | the same, for version 1.0 |
| `https://w3id.org/weft/context.jsonld` | the JSON-LD context |
| `https://w3id.org/weft/shapes` | the SHACL shapes |

Term IRIs such as `https://w3id.org/weft#used` work through the first rule: the browser
requests `https://w3id.org/weft` and keeps `#used`, so it opens that term's section.

## Steps (about ten minutes, all in the browser)

1. Check that <https://rishirajani.github.io/weft/> is live. w3id.org asks for the target to
   be live before you open the pull request.
2. Open <https://github.com/perma-id/w3id.org> and click **Fork**, then **Create fork**.
3. In your fork, click **Add file → Create new file**. As the name, type
   `ids/weft/.htaccess` (typing the slashes creates the folders).
4. Paste the contents of [`ids/weft/.htaccess`](ids/weft/.htaccess) from this repository.
5. Commit directly to your fork's main branch with the message
   `weft: add permanent identifiers for the Weft vocabulary`.
6. GitHub shows **Contribute → Open pull request**. Use the title
   `weft: add permanent identifiers for the Weft vocabulary` and this description:

   > Adds `/weft/` for Weft, an open OWL vocabulary (CC BY 4.0) for evidence-backed career
   > graphs, built on schema.org. The namespace is `https://w3id.org/weft#`; the rules
   > content-negotiate between the HTML documentation and Turtle, JSON-LD, RDF/XML and
   > N-Triples on GitHub Pages, with version IRIs (`/weft/1.0`), the JSON-LD context and
   > the SHACL shapes. Source: https://github.com/rishirajani/weft. Maintainer: @rishirajani.

7. Tick the checklist in the pull request template. The automatic checks run on the
   pull request; if they comment on a line, tell me what they say.

A maintainer reviews and merges it, usually within days. After that, these should all work:

```sh
curl -sIL https://w3id.org/weft | grep -i location
curl -sIL -H 'Accept: text/turtle' https://w3id.org/weft | grep -i location
```

## Changing the rules later

Edit `ids/weft/.htaccess` in your fork the same way and open another pull request. Because the
file names you as maintainer, w3id.org reviewers will ask you to approve any change to it
that someone else proposes.
