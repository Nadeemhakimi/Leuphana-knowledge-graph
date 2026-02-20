"""
Natural Language to SPARQL chain for the Leuphana Knowledge Graph.

Uses LangChain with OpenAI GPT-4 to translate natural language questions
into SPARQL queries, execute them against GraphDB, and return results.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Configuration
GRAPHDB_ENDPOINT = os.getenv(
    "GRAPHDB_ENDPOINT", "http://localhost:7200"
)
GRAPHDB_REPOSITORY = os.getenv("GRAPHDB_REPOSITORY", "leuphana-kg")
QUERY_ENDPOINT = f"{GRAPHDB_ENDPOINT}/repositories/{GRAPHDB_REPOSITORY}"
ONTOLOGY_PATH = str(PROJECT_ROOT / "ontology" / "leuphana.owl")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")

# Module-level cache
_chain = None


def _load_ontology_schema():
    """Load and parse the ontology file to extract schema information for the LLM."""
    from rdflib import Graph, RDF, RDFS, OWL, Namespace

    g = Graph()
    g.parse(ONTOLOGY_PATH, format="xml")

    LEUPH = Namespace("http://leuphana.de/ontology#")

    schema_parts = []
    schema_parts.append("Ontology: Leuphana University Knowledge Graph")
    schema_parts.append("Prefix: leuph: <http://leuphana.de/ontology#>")
    schema_parts.append("")

    # Extract classes
    schema_parts.append("Classes:")
    for cls in g.subjects(RDF.type, OWL.Class):
        cls_str = str(cls)
        if "leuphana.de/ontology#" in cls_str:
            local_name = cls_str.split("#")[-1]
            comment = g.value(cls, RDFS.comment)
            label = g.value(cls, RDFS.label)
            superclass = g.value(cls, RDFS.subClassOf)
            super_name = str(superclass).split("#")[-1] if superclass else ""
            line = f"  - leuph:{local_name}"
            if super_name and "leuphana.de" in str(superclass):
                line += f" (subClassOf leuph:{super_name})"
            if comment:
                line += f" - {comment}"
            schema_parts.append(line)

    schema_parts.append("")

    # Extract object properties
    schema_parts.append("Object Properties (relationships between entities):")
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        prop_str = str(prop)
        if "leuphana.de/ontology#" in prop_str:
            local_name = prop_str.split("#")[-1]
            domain = g.value(prop, RDFS.domain)
            range_val = g.value(prop, RDFS.range)
            domain_name = str(domain).split("#")[-1] if domain else "Thing"
            range_name = str(range_val).split("#")[-1] if range_val else "Thing"
            comment = g.value(prop, RDFS.comment)
            line = f"  - leuph:{local_name}: {domain_name} -> {range_name}"
            if comment:
                line += f" ({comment})"
            schema_parts.append(line)

    schema_parts.append("")

    # Extract data properties
    schema_parts.append("Data Properties (attributes):")
    for prop in g.subjects(RDF.type, OWL.DatatypeProperty):
        prop_str = str(prop)
        if "leuphana.de/ontology#" in prop_str:
            local_name = prop_str.split("#")[-1]
            domain = g.value(prop, RDFS.domain)
            range_val = g.value(prop, RDFS.range)
            domain_name = str(domain).split("#")[-1] if domain else "Thing"
            range_name = str(range_val).split("#")[-1] if range_val else "string"
            schema_parts.append(f"  - leuph:{local_name}: {domain_name} -> {range_name}")

    return "\n".join(schema_parts)


SPARQL_GENERATION_PROMPT = """You are a SPARQL query generator for the Leuphana University Knowledge Graph stored in GraphDB.

Given the ontology schema below and a natural language question, generate a valid SPARQL SELECT query.

SCHEMA:
{schema}

{sample_data}

RULES:
1. Use ONLY the classes and properties defined in the schema above.
2. Always include the PREFIX declaration: PREFIX leuph: <http://leuphana.de/ontology#>
3. Use leuph:name to get human-readable names for entities.
4. Return ONLY the SPARQL query, no explanations.
5. For person queries, the class hierarchy is: Person > AcademicStaff > Professor, PostDoc, PhDStudent, etc.
6. The organizational hierarchy is: University > School > Institute > Chair.
   IMPORTANT: leuph:partOf ONLY connects adjacent levels. The data contains:
   - Chair partOf Institute
   - Institute partOf School
   - School partOf University
   There are NO direct links like Chair partOf School or Institute partOf University.
   To traverse multiple levels, chain intermediate variables:
   CORRECT: ?chair leuph:partOf ?institute . ?institute leuph:partOf ?school .
   WRONG:   ?chair leuph:partOf ?school .
7. Use OPTIONAL for properties that might not exist on all entities.
8. Use ORDER BY for readable results.
9. Use LIMIT 100 unless the user asks for all results or a count.
10. For counting queries, use COUNT with GROUP BY where appropriate.
11. People (professors, staff) are linked to organizational units via leuph:worksAt.
    A person may worksAt a Chair or an Institute. To find their School, traverse up:
    ?person leuph:worksAt ?unit . ?unit leuph:partOf* ?school . ?school a leuph:School .
12. When a user says "department", it could mean Chair OR Institute. Prefer not restricting
    to a single type unless the user is specific. Use:
    ?person leuph:worksAt ?dept . ?dept leuph:name ?deptName .
    without "?dept a leuph:Chair" unless the user explicitly says "chair".
13. When the user asks about a specific named entity, use FILTER with CONTAINS or regex
    for fuzzy matching, since exact names may differ:
    FILTER(CONTAINS(LCASE(?name), LCASE("search term")))
14. Prefer inclusive queries. If unsure whether an entity is typed as Chair or Institute,
    omit the type constraint and let the results show what exists.

EXAMPLES:
- "Which chairs belong to which school/faculty?"
  PREFIX leuph: <http://leuphana.de/ontology#>
  SELECT ?chairName ?instituteName ?schoolName WHERE {{
    ?chair a leuph:Chair ; leuph:name ?chairName ; leuph:partOf ?institute .
    ?institute a leuph:Institute ; leuph:name ?instituteName ; leuph:partOf ?school .
    ?school a leuph:School ; leuph:name ?schoolName .
  }} ORDER BY ?schoolName ?instituteName ?chairName

- "Which professors work at the School of Sustainability?"
  PREFIX leuph: <http://leuphana.de/ontology#>
  SELECT ?profName ?unitName WHERE {{
    ?prof a leuph:Professor ; leuph:name ?profName ; leuph:worksAt ?unit .
    ?unit leuph:name ?unitName ; leuph:partOf* ?school .
    ?school a leuph:School ; leuph:name ?schoolName .
    FILTER(CONTAINS(LCASE(?schoolName), "sustainability"))
  }} ORDER BY ?profName

- "How many chairs does each institute have?"
  PREFIX leuph: <http://leuphana.de/ontology#>
  SELECT ?instituteName (COUNT(?chair) AS ?chairCount) WHERE {{
    ?chair a leuph:Chair ; leuph:partOf ?institute .
    ?institute a leuph:Institute ; leuph:name ?instituteName .
  }} GROUP BY ?instituteName ORDER BY DESC(?chairCount)

- "Which professors work in which department?"
  PREFIX leuph: <http://leuphana.de/ontology#>
  SELECT ?profName ?deptName WHERE {{
    ?prof a leuph:Professor ; leuph:name ?profName ; leuph:worksAt ?dept .
    ?dept leuph:name ?deptName .
  }} ORDER BY ?profName LIMIT 100

QUESTION: {question}

SPARQL Query:"""


SPARQL_RETRY_PROMPT = """The previous SPARQL query failed or returned no results.

Previous query:
{previous_query}

Error/Issue: {error}

Original question: {question}

Please generate a corrected SPARQL query. Common fixes:
- Remove overly restrictive type constraints (e.g., don't require ?x a leuph:Chair if it might be an Institute)
- Use leuph:partOf* for multi-hop traversals instead of direct links
- Use OPTIONAL for properties that might not exist
- Use FILTER(CONTAINS(...)) instead of exact string matching
- Check that the property direction is correct (domain -> range)

Return ONLY the corrected SPARQL query:"""


ANSWER_PROMPT = """Based on the SPARQL query results below, provide a concise natural language answer to the user's question.

Question: {question}
Results: {results}

If there are no results, say so. Keep your answer brief and informative. Just answer the question directly."""


def _fetch_sample_data():
    """Fetch sample entity names from GraphDB to give the LLM real data context."""
    sample_query = """
    PREFIX leuph: <http://leuphana.de/ontology#>
    SELECT ?type ?name WHERE {
        { ?e a leuph:School ; leuph:name ?name . BIND("School" AS ?type) }
        UNION
        { ?e a leuph:Institute ; leuph:name ?name . BIND("Institute" AS ?type) }
        UNION
        { ?e a leuph:Chair ; leuph:name ?name . BIND("Chair" AS ?type) }
        UNION
        { ?e a leuph:Professor ; leuph:name ?name . BIND("Professor" AS ?type) }
        UNION
        { ?e a leuph:BachelorProgram ; leuph:name ?name . BIND("BachelorProgram" AS ?type) }
        UNION
        { ?e a leuph:MasterProgram ; leuph:name ?name . BIND("MasterProgram" AS ?type) }
    } LIMIT 50
    """
    try:
        results = execute_sparql(sample_query)
        bindings = results.get("results", {}).get("bindings", [])
        if not bindings:
            return ""

        by_type = {}
        for row in bindings:
            t = row.get("type", {}).get("value", "")
            n = row.get("name", {}).get("value", "")
            if t and n:
                by_type.setdefault(t, []).append(n)

        parts = ["SAMPLE DATA (real entity names in the graph):"]
        for t, names in sorted(by_type.items()):
            examples = ", ".join(f'"{n}"' for n in names[:5])
            parts.append(f"  {t}: {examples}")

        return "\n".join(parts)
    except Exception:
        return ""


def _get_chain():
    """Initialize and cache the LLM chain components."""
    global _chain
    if _chain is not None:
        return _chain

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key == "sk-your-key-here":
        raise ValueError(
            "OPENAI_API_KEY not configured. Please set it in your .env file."
        )

    from langchain_openai import ChatOpenAI
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import StrOutputParser

    llm = ChatOpenAI(
        temperature=0,
        model_name=OPENAI_MODEL,
        openai_api_key=api_key,
    )

    schema = _load_ontology_schema()
    sample_data = _fetch_sample_data()

    base_template = SPARQL_GENERATION_PROMPT.replace("{schema}", schema)
    base_template = base_template.replace("{sample_data}", sample_data)

    sparql_prompt = PromptTemplate(
        input_variables=["question"],
        template=base_template,
    )

    answer_prompt = PromptTemplate(
        input_variables=["question", "results"],
        template=ANSWER_PROMPT,
    )

    retry_prompt = PromptTemplate(
        input_variables=["previous_query", "error", "question"],
        template=SPARQL_RETRY_PROMPT,
    )

    sparql_chain = sparql_prompt | llm | StrOutputParser()
    answer_chain = answer_prompt | llm | StrOutputParser()
    retry_chain = retry_prompt | llm | StrOutputParser()

    _chain = {
        "sparql_chain": sparql_chain,
        "answer_chain": answer_chain,
        "retry_chain": retry_chain,
        "schema": schema,
    }
    return _chain


def execute_sparql(query: str) -> dict:
    """Execute a SPARQL query against GraphDB and return JSON results."""
    if not query.strip():
        return {}

    encoded_query = urllib.parse.urlencode({"query": query})

    req = urllib.request.Request(
        QUERY_ENDPOINT,
        data=encoded_query.encode("utf-8"),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/sparql-results+json",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GraphDB error ({e.code}): {error_body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"Cannot connect to GraphDB at {QUERY_ENDPOINT}: {e.reason}")


def _clean_sparql(raw: str) -> str:
    """Extract clean SPARQL from LLM output (strip markdown fences, etc.)."""
    query = raw.strip()

    # Remove markdown code fences if present
    if query.startswith("```"):
        lines = query.split("\n")
        # Remove first and last lines if they are fences
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        query = "\n".join(lines)

    return query.strip()


def ask_question(question: str) -> dict:
    """
    Process a natural language question about the Leuphana Knowledge Graph.

    Returns:
        dict with keys: sparql, results, answer, success, error (if failed)
    """
    try:
        chain = _get_chain()
    except ValueError as e:
        return {
            "sparql": "",
            "results": {},
            "answer": "",
            "error": str(e),
            "success": False,
        }

    max_retries = 2
    sparql_query = ""
    last_error = ""

    try:
        # Step 1: Generate SPARQL from natural language
        raw_sparql = chain["sparql_chain"].invoke({"question": question})
        sparql_query = _clean_sparql(raw_sparql)

        print(f"  Generated SPARQL:\n{sparql_query}")

        # Step 2: Execute with retry logic
        for attempt in range(max_retries + 1):
            try:
                results = execute_sparql(sparql_query)
                bindings = results.get("results", {}).get("bindings", [])
                print(f"  Query returned {len(bindings)} results (attempt {attempt + 1})")

                # If no results on first attempt, retry with relaxed query
                if len(bindings) == 0 and attempt < max_retries:
                    print("  No results, retrying with relaxed query...")
                    raw_retry = chain["retry_chain"].invoke({
                        "previous_query": sparql_query,
                        "error": "Query returned 0 results. The query may be too restrictive.",
                        "question": question,
                    })
                    sparql_query = _clean_sparql(raw_retry)
                    print(f"  Retry SPARQL:\n{sparql_query}")
                    continue

                break  # Got results, exit retry loop

            except RuntimeError as e:
                last_error = str(e)
                if attempt < max_retries and "error" in last_error.lower():
                    print(f"  Query failed (attempt {attempt + 1}): {last_error}")
                    raw_retry = chain["retry_chain"].invoke({
                        "previous_query": sparql_query,
                        "error": last_error,
                        "question": question,
                    })
                    sparql_query = _clean_sparql(raw_retry)
                    print(f"  Retry SPARQL:\n{sparql_query}")
                    continue
                raise

        # Step 3: Generate natural language answer
        results_summary = []
        for row in bindings[:20]:
            row_data = {k: v.get("value", "") for k, v in row.items()}
            results_summary.append(row_data)

        results_text = json.dumps(results_summary, indent=2) if results_summary else "No results found."
        if len(bindings) > 20:
            results_text += f"\n... and {len(bindings) - 20} more results."

        answer = chain["answer_chain"].invoke({
            "question": question,
            "results": results_text,
        })

        return {
            "sparql": sparql_query,
            "results": results,
            "answer": answer,
            "success": True,
        }

    except RuntimeError as e:
        return {
            "sparql": sparql_query,
            "results": {},
            "answer": "",
            "error": str(e),
            "success": False,
        }
    except Exception as e:
        return {
            "sparql": sparql_query,
            "results": {},
            "answer": "",
            "error": f"Error: {str(e)}",
            "success": False,
        }


if __name__ == "__main__":
    """Test the chain from command line."""
    if len(sys.argv) < 2:
        print("Usage: python nlq_chain.py 'Your question here'")
        sys.exit(1)

    question = " ".join(sys.argv[1:])
    print(f"\nQuestion: {question}")
    print("-" * 60)

    result = ask_question(question)

    if result["success"]:
        print(f"\nSPARQL:\n{result['sparql']}")
        print(f"\nAnswer: {result['answer']}")
        bindings = result["results"].get("results", {}).get("bindings", [])
        print(f"\nResults: {len(bindings)} rows")
    else:
        print(f"\nError: {result['error']}")
