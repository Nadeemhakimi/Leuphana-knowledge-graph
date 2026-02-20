# Leuphana University Knowledge Graph

A Knowledge Graph (KG) representing the organizational and academic structure of Leuphana University of Lüneburg.

## Project Overview

This project creates a machine-readable representation of Leuphana's academic structure, enabling unified querying of relationships such as:

- Which professors work in which department?
- **Who teaches which courses in which major?** (Professor → teaches → Course → partOf → Program)
- Which institutes belong to which school?
- Which chairs (Lehrstühle) exist and who heads them?
- What HiWi positions are currently available?
- Which research projects are conducted by which institutes?

## Project Structure

```
leuphana-kg/
├── ontology/                    # Ontology & validation files
│   ├── leuphana.owl             # Main OWL 2 ontology
│   ├── shacl_shapes.ttl         # SHACL validation shapes
│   └── ontology_documentation.md
├── scraper/                     # Python source code
│   ├── config.py                # Scraper configuration & URL patterns
│   ├── scraper.py               # Web scraper (extracts all entities)
│   ├── rdf_generator.py         # RDF triple generation
│   ├── graphdb_integration.py   # GraphDB client
│   ├── query_interface.py       # Query interface
│   └── visualization.py         # Visualization export tools
├── visualization/               # Interactive visualization
│   ├── index.html               # D3.js visualization with NLQ interface
│   ├── server.py                # HTTP server + SPARQL proxy + NLQ endpoint
│   ├── nlq_chain.py             # LangChain NLQ-to-SPARQL translation
│   └── d3_graph.json            # Graph data for visualization
├── queries/                     # Query files
│   └── sparql_queries.rq        # SPARQL queries for all CQs
├── data/                        # Data files
│   ├── raw/                     # Scraped JSON data
│   └── rdf/                     # Generated RDF (Turtle format)
├── sitemapurls.txt              # University sitemap URLs (7000+ pages)
├── .env.example                 # Environment configuration template
├── requirements.txt
└── README.md
```

## Entity Types Extracted

| Entity          | Description                                    | Count (approx.) |
| --------------- | ---------------------------------------------- | --------------- |
| University      | Leuphana University                            | 1               |
| School          | Faculty units (College, Graduate School, etc.) | 4               |
| Institute       | Academic institutes                            | 20+             |
| Chair           | Professorships/Lehrstühle                      | 30+             |
| Person          | Professors, staff, researchers                 | 1000+           |
| BachelorProgram | Bachelor degree programs                       | 15+             |
| MasterProgram   | Master degree programs                         | 40+             |
| Minor           | Minor study fields (Nebenfächer)               | 20+             |
| Course          | Courses/modules with instructors               | varies          |
| HiWiPosition    | Student assistant positions                    | varies          |
| ResearchProject | Research projects                              | 100+            |
| ResearchCenter  | Research centers (Zentren)                     | 10+             |

## Quick Start

### Step 1: Install Dependencies

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### Step 2: Run the Web Scraper

```bash
# Full extraction using sitemap
python scraper/scraper.py --sitemap sitemapurls.txt
```

The scraper extracts:

- Organizations (University, Schools, Institutes, Research Centers)
- Chairs (Professorships/Lehrstühle)
- Persons (all categories from sitemap)
- Study Programs (Bachelor, Master)
- Minor Programs
- Courses (from Vorlesungsverzeichnis)
- HiWi Positions
- Research Projects

Output is saved to `data/raw/latest.json`

### Step 3: Generate RDF Triples

```bash
python scraper/rdf_generator.py
```

This converts the JSON data to RDF triples using the Leuphana ontology.
Output is saved to `data/rdf/leuphana_kg_latest.ttl`

### Step 4: Setup GraphDB & Import Data

#### Install GraphDB Free

1. Download from: https://www.ontotext.com/products/graphdb/download/
2. Extract and run:

   ```bash
   # Linux/Mac
   ./graphdb-free -d

   # Or run the desktop application
   ```

3. Access GraphDB Workbench: http://localhost:7200

#### Create Repository

**Option A: Using Python client**

```bash
python scraper/graphdb_integration.py create
```

**Option B: Manual setup in GraphDB Workbench**

1. Go to "Setup" → "Repositories" → "Create new repository"
2. Choose "GraphDB Repository"
3. Repository ID: `leuphana-kg`
4. Ruleset: `RDFS-Plus (Optimized)`
5. Click "Create"

#### Import RDF Data

**Option A: Using Python client**

```bash
python scraper/graphdb_integration.py import data/rdf/leuphana_kg_latest.ttl
```

**Option B: Using GraphDB Workbench**

1. Go to "Import" → "RDF" → "Upload RDF files"
2. Select `data/rdf/leuphana_kg_latest.ttl`
3. Click "Import"

#### Verify Import

```bash
# Check statistics
python scraper/graphdb_integration.py stats

# Or in GraphDB Workbench: go to "Explore" → "Graphs overview"
```

### Step 5: Visualize the Knowledge Graph

#### Option A: Interactive D3.js Visualization

```bash
# Generate D3 JSON from RDF (required after each scrape/RDF generation)
python scraper/visualization.py d3 data/rdf/leuphana_kg_latest.ttl visualization/d3_graph.json

# Start visualization server (with SPARQL proxy)
python visualization/server.py
```

Open http://localhost:8000 in your browser.

Features:

- Natural language querying (ask questions in plain English, LLM generates SPARQL)
- Force-directed graph layout with D3.js
- Node filtering by type
- Search functionality
- SPARQL query integration (connects to GraphDB)
- Auto-highlighting of query results in graph
- Click nodes for details
- Export results as CSV

**Regenerate after cleanup:**

```bash
# If you deleted d3_graph.json, regenerate it with:
python scraper/visualization.py d3 data/rdf/leuphana_kg_latest.ttl visualization/d3_graph.json
```

#### Option B: GraphDB Visual Graph

1. Open GraphDB Workbench: http://localhost:7200
2. Go to "Explore" → "Visual Graph"
3. Enter a starting URI, e.g.: `http://leuphana.de/resource/university/leuphana`
4. Explore relationships visually

#### Option C: SPARQL Query Results

```bash
# Run predefined queries
python scraper/graphdb_integration.py query all_schools
python scraper/graphdb_integration.py query professors_by_institute

# Run custom SPARQL
python scraper/graphdb_integration.py query --sparql "
PREFIX leuph: <http://leuphana.de/ontology#>
SELECT ?prof ?course WHERE {
    ?prof leuph:teaches ?course .
    ?prof leuph:name ?name .
}
LIMIT 20
"
```

## Running SPARQL Queries

### Using the Visualization UI (Natural Language Queries)

1. Start the server: `python visualization/server.py`
2. Open http://localhost:8000 in your browser
3. Type a question in plain English (e.g., "Which professors work in the School of Sustainability?")
4. The LLM translates your question to SPARQL, executes it, and displays results
5. Results are shown in both a table and highlighted in the graph

The NLQ feature requires an OpenAI API key configured in `.env` (see Configuration below).

### Using Python

```python
from scraper.graphdb_integration import GraphDBClient, SPARQLQueryRunner

client = GraphDBClient(repository="leuphana-kg")
runner = SPARQLQueryRunner(client)

# Example: Find who teaches which courses
results = client.query("""
    PREFIX leuph: <http://leuphana.de/ontology#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT ?professorName ?courseName ?programName WHERE {
        ?professor leuph:teaches ?course .
        ?professor leuph:name ?professorName .
        ?course leuph:name ?courseName .
        OPTIONAL {
            ?course leuph:partOf ?program .
            ?program leuph:name ?programName .
        }
    }
    LIMIT 50
""")

for row in results:
    print(f"{row['professorName']} teaches {row['courseName']}")
```

### Using Command Line

```bash
# List available predefined queries
python scraper/graphdb_integration.py list

# Run a predefined query
python scraper/graphdb_integration.py query all_professors
python scraper/graphdb_integration.py query chairs_with_heads

# Export query results to CSV
python scraper/graphdb_integration.py query all_professors --output results.csv
```

## Competency Questions

The Knowledge Graph answers these questions:

| #   | Question                                     | SPARQL Pattern                                                |
| --- | -------------------------------------------- | ------------------------------------------------------------- |
| CQ1 | Which professors work in which institute?    | `?prof leuph:worksAt ?institute`                              |
| CQ2 | Who teaches which courses in which program?  | `?prof leuph:teaches ?course . ?course leuph:partOf ?program` |
| CQ3 | Which institutes belong to which school?     | `?institute leuph:partOf ?school`                             |
| CQ4 | Who heads which chair (Lehrstuhl)?           | `?prof leuph:heads ?chair`                                    |
| CQ5 | What HiWi positions are available?           | `?pos a leuph:HiWiPosition`                                   |
| CQ6 | What is the contact info for staff?          | `?person leuph:email ?email ; leuph:phone ?phone`             |
| CQ7 | Which programs are offered by which school?  | `?program leuph:offeredBy ?school`                            |
| CQ8 | Which research projects are conducted where? | `?project leuph:conductedBy ?org`                             |

## Key Relationships

```
University
    └── hasPart → School
                    └── hasPart → Institute
                                    └── hasPart → Chair
                                                    └── headed by ← Professor
                                                                      └── teaches → Course
                                                                                      └── partOf → Program
```

## Configuration

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```
GRAPHDB_ENDPOINT=http://localhost:7200
GRAPHDB_REPOSITORY=leuphana-kg

# Required for Natural Language Query feature
OPENAI_API_KEY=sk-your-key-here
OPENAI_MODEL=gpt-4
```

## Technology Stack

| Component      | Technology                        |
| -------------- | --------------------------------- |
| Ontology       | OWL 2 (Protégé)                   |
| Web Scraping   | Python, BeautifulSoup, requests   |
| RDF Generation | RDFLib                            |
| Triple Store   | GraphDB Free                      |
| Query Language | SPARQL 1.1                        |
| NLQ Engine     | LangChain + OpenAI GPT-4          |
| Validation     | SHACL                             |
| Visualization  | D3.js (force-directed graph)      |
| UI Framework   | Tailwind CSS                      |

## Troubleshooting

### GraphDB connection issues

```bash
# Check if GraphDB is running
curl http://localhost:7200/repositories

# Check status via Python
python scraper/graphdb_integration.py status
```

### Empty visualization

1. Ensure RDF was generated: check `data/rdf/leuphana_kg_latest.ttl` exists
2. Regenerate D3 JSON: `python scraper/visualization.py`
3. Clear browser cache and reload

### Scraper errors

```bash
# Run with verbose output
python scraper/scraper.py --sitemap sitemapurls.txt 2>&1 | tee scraper.log
```

## Quick Reference Commands

```bash
# 1. Scrape ALL data (always use --sitemap for complete extraction)
python scraper/scraper.py --sitemap sitemapurls.txt

# 2. Generate RDF triples from scraped data
python scraper/rdf_generator.py

# 3. Generate D3 visualization JSON
python scraper/visualization.py d3 data/rdf/leuphana_kg_latest.ttl visualization/d3_graph.json

# 4. Import to GraphDB (requires GraphDB running on localhost:7200)
python scraper/graphdb_integration.py import data/rdf/leuphana_kg_latest.ttl

# 5. Start visualization server (opens on http://localhost:8000)
python visualization/server.py
```

**Important**: Always use `--sitemap sitemapurls.txt` to extract all available data from the university website.

## Documentation

- [Ontology Documentation](ontology/ontology_documentation.md) - Ontology design decisions
- 
## License

Academic use - Bachelor's Thesis Project

## Author: Nadeem Hakimi

Bachelor's Thesis Project - Leuphana University of Lüneburg

Supervisor: Dr.Debayan Banerjee
