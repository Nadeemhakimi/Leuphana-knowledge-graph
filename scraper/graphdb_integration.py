#!/usr/bin/env python3
"""
Leuphana University Knowledge Graph - GraphDB Integration

This module provides integration with Ontotext GraphDB Free.
GraphDB is a semantic graph database that supports SPARQL 1.1.

Author: Bachelor's Thesis Project
Supervisor: Debayan Banerjee

Setup GraphDB Free:
    1. Download from: https://www.ontotext.com/products/graphdb/download/
    2. Run: ./graphdb-free -d
    3. Access at: http://localhost:7200
    4. Create a repository named "leuphana-kg"

Usage:
    from graphdb_integration import GraphDBClient
    
    client = GraphDBClient()
    client.create_repository("leuphana-kg")
    client.import_rdf("data/rdf/leuphana_kg_latest.ttl")
    results = client.query("SELECT * WHERE { ?s ?p ?o } LIMIT 10")
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass


class GraphDBClient:
    """
    Client for interacting with Ontotext GraphDB.
    
    Supports:
    - Repository management
    - RDF import (Turtle, N-Triples, RDF/XML)
    - SPARQL queries (SELECT, CONSTRUCT, ASK)
    - SPARQL updates (INSERT, DELETE)
    """
    
    def __init__(
        self,
        endpoint: str = None,
        repository: str = None,
        username: str = None,
        password: str = None
    ):
        """
        Initialize GraphDB client.
        
        Args:
            endpoint: GraphDB base URL (default: http://localhost:7200)
            repository: Repository name (default: leuphana-kg)
            username: Optional username for authentication
            password: Optional password for authentication
        """
        self.endpoint = endpoint or os.getenv("GRAPHDB_ENDPOINT", "http://localhost:7200")
        self.repository = repository or os.getenv("GRAPHDB_REPOSITORY", "leuphana-kg")
        self.username = username or os.getenv("GRAPHDB_USER")
        self.password = password or os.getenv("GRAPHDB_PASSWORD")
        
        self.session = requests.Session()
        if self.username and self.password:
            self.session.auth = (self.username, self.password)
        
        # Common headers
        self.session.headers.update({
            "Accept": "application/json"
        })
    
    @property
    def sparql_endpoint(self) -> str:
        """Get the SPARQL query endpoint URL."""
        return f"{self.endpoint}/repositories/{self.repository}"
    
    @property
    def update_endpoint(self) -> str:
        """Get the SPARQL update endpoint URL."""
        return f"{self.endpoint}/repositories/{self.repository}/statements"
    
    def check_connection(self) -> bool:
        """Check if GraphDB is accessible."""
        try:
            response = self.session.get(f"{self.endpoint}/rest/repositories")
            return response.status_code == 200
        except requests.RequestException:
            return False
    
    def list_repositories(self) -> List[str]:
        """List all available repositories."""
        response = self.session.get(f"{self.endpoint}/rest/repositories")
        response.raise_for_status()
        return [repo["id"] for repo in response.json()]
    
    def repository_exists(self, repo_name: str = None) -> bool:
        """Check if a repository exists."""
        repo_name = repo_name or self.repository
        return repo_name in self.list_repositories()
    
    def create_repository(self, repo_name: str = None, ruleset: str = "rdfsplus-optimized"):
        """
        Create a new repository.
        
        Args:
            repo_name: Repository name (default: self.repository)
            ruleset: Inference ruleset (default: rdfsplus-optimized)
                Options: empty, rdfs, owl-horst, owl-max, rdfsplus-optimized
        """
        repo_name = repo_name or self.repository
        
        if self.repository_exists(repo_name):
            print(f"Repository '{repo_name}' already exists")
            return
        
        # Repository configuration
        config = {
            "id": repo_name,
            "type": "graphdb",
            "title": f"Leuphana Knowledge Graph - {repo_name}",
            "params": {
                "ruleset": {"value": ruleset},
                "enableContextIndex": {"value": "true"},
                "enablePredicateList": {"value": "true"},
                "inMemoryLiteralProperties": {"value": "true"},
                "enableLiteralIndex": {"value": "true"}
            }
        }
        
        response = self.session.post(
            f"{self.endpoint}/rest/repositories",
            json=config
        )
        
        if response.status_code in (200, 201):
            print(f"Repository '{repo_name}' created successfully")
            self.repository = repo_name
        else:
            raise Exception(f"Failed to create repository: {response.text}")
    
    def delete_repository(self, repo_name: str = None):
        """Delete a repository."""
        repo_name = repo_name or self.repository
        
        response = self.session.delete(
            f"{self.endpoint}/rest/repositories/{repo_name}"
        )
        
        if response.status_code == 200:
            print(f"Repository '{repo_name}' deleted")
        else:
            raise Exception(f"Failed to delete repository: {response.text}")
    
    def clear_repository(self):
        """Clear all data from the current repository."""
        response = self.session.delete(self.update_endpoint)
        
        if response.status_code == 204:
            print(f"Repository '{self.repository}' cleared")
        else:
            raise Exception(f"Failed to clear repository: {response.text}")
    
    def import_rdf(
        self,
        file_path: str,
        format: str = None,
        named_graph: str = None
    ):
        """
        Import RDF data from a file.
        
        Args:
            file_path: Path to RDF file
            format: RDF format (auto-detected if None)
                Options: turtle, ntriples, rdfxml, jsonld, trig
            named_graph: Optional named graph URI
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"RDF file not found: {file_path}")
        
        # Auto-detect format
        if format is None:
            format_map = {
                ".ttl": "text/turtle",
                ".nt": "application/n-triples",
                ".rdf": "application/rdf+xml",
                ".xml": "application/rdf+xml",
                ".jsonld": "application/ld+json",
                ".json": "application/ld+json",
                ".trig": "application/trig"
            }
            content_type = format_map.get(file_path.suffix.lower(), "text/turtle")
        else:
            format_types = {
                "turtle": "text/turtle",
                "ntriples": "application/n-triples",
                "rdfxml": "application/rdf+xml",
                "jsonld": "application/ld+json",
                "trig": "application/trig"
            }
            content_type = format_types.get(format, "text/turtle")
        
        # Build URL with optional named graph
        url = self.update_endpoint
        if named_graph:
            url += f"?context=<{named_graph}>"
        
        # Read and upload file
        with open(file_path, "rb") as f:
            data = f.read()
        
        response = self.session.post(
            url,
            data=data,
            headers={"Content-Type": content_type}
        )
        
        if response.status_code in (200, 204):
            print(f"Successfully imported {file_path}")
        else:
            raise Exception(f"Import failed: {response.status_code} - {response.text}")
    
    def query(
        self,
        sparql: str,
        timeout: int = 30000,
        return_format: str = "json"
    ) -> Dict[str, Any]:
        """
        Execute a SPARQL SELECT or ASK query.
        
        Args:
            sparql: SPARQL query string
            timeout: Query timeout in milliseconds
            return_format: Response format (json, xml, csv)
        
        Returns:
            Query results as dictionary
        """
        accept_types = {
            "json": "application/sparql-results+json",
            "xml": "application/sparql-results+xml",
            "csv": "text/csv"
        }
        
        response = self.session.post(
            self.sparql_endpoint,
            data={"query": sparql, "timeout": timeout},
            headers={"Accept": accept_types.get(return_format, accept_types["json"])}
        )
        
        response.raise_for_status()
        
        if return_format == "json":
            return response.json()
        return response.text
    
    def construct(self, sparql: str, format: str = "turtle") -> str:
        """
        Execute a SPARQL CONSTRUCT query.
        
        Args:
            sparql: SPARQL CONSTRUCT query
            format: Output format (turtle, ntriples, rdfxml, jsonld)
        
        Returns:
            RDF data as string
        """
        accept_types = {
            "turtle": "text/turtle",
            "ntriples": "application/n-triples",
            "rdfxml": "application/rdf+xml",
            "jsonld": "application/ld+json"
        }
        
        response = self.session.post(
            self.sparql_endpoint,
            data={"query": sparql},
            headers={"Accept": accept_types.get(format, "text/turtle")}
        )
        
        response.raise_for_status()
        return response.text
    
    def update(self, sparql: str):
        """
        Execute a SPARQL UPDATE query (INSERT/DELETE).
        
        Args:
            sparql: SPARQL UPDATE query
        """
        response = self.session.post(
            f"{self.sparql_endpoint}/statements",
            data={"update": sparql},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code not in (200, 204):
            raise Exception(f"Update failed: {response.text}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get repository statistics."""
        stats_query = """
        SELECT 
            (COUNT(DISTINCT ?s) AS ?subjects)
            (COUNT(DISTINCT ?p) AS ?predicates)
            (COUNT(DISTINCT ?o) AS ?objects)
            (COUNT(*) AS ?triples)
        WHERE { ?s ?p ?o }
        """
        
        result = self.query(stats_query)
        bindings = result.get("results", {}).get("bindings", [])
        
        if bindings:
            return {
                "subjects": int(bindings[0]["subjects"]["value"]),
                "predicates": int(bindings[0]["predicates"]["value"]),
                "objects": int(bindings[0]["objects"]["value"]),
                "triples": int(bindings[0]["triples"]["value"])
            }
        return {}
    
    def get_entity_counts(self) -> Dict[str, int]:
        """Get counts of entities by type."""
        count_query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        
        SELECT ?type (COUNT(?s) AS ?count)
        WHERE {
            ?s rdf:type ?type .
        }
        GROUP BY ?type
        ORDER BY DESC(?count)
        """
        
        result = self.query(count_query)
        bindings = result.get("results", {}).get("bindings", [])
        
        counts = {}
        for binding in bindings:
            type_uri = binding["type"]["value"]
            type_name = type_uri.split("#")[-1].split("/")[-1]
            counts[type_name] = int(binding["count"]["value"])
        
        return counts


class SPARQLQueryRunner:
    """
    Convenience class for running predefined SPARQL queries.
    Maps natural language questions to SPARQL queries.
    """
    
    # Predefined SPARQL queries for competency questions
    QUERIES = {
        "all_schools": {
            "description": "List all schools/faculties",
            "query": """
                PREFIX leuph: <http://leuphana.de/ontology#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
                
                SELECT ?school ?name ?description
                WHERE {
                    ?school a leuph:School .
                    ?school leuph:name ?name .
                    OPTIONAL { ?school leuph:description ?description }
                }
                ORDER BY ?name
            """
        },
        
        "all_institutes": {
            "description": "List all institutes with their schools",
            "query": """
                PREFIX leuph: <http://leuphana.de/ontology#>
                
                SELECT ?institute ?name ?abbreviation ?schoolName
                WHERE {
                    ?institute a leuph:Institute .
                    ?institute leuph:name ?name .
                    OPTIONAL { ?institute leuph:abbreviation ?abbreviation }
                    OPTIONAL {
                        ?institute leuph:partOf|leuph:belongsTo ?school .
                        ?school leuph:name ?schoolName .
                    }
                }
                ORDER BY ?schoolName ?name
            """
        },
        
        "professors_by_school": {
            "description": "Which professors work in which school?",
            "query": """
                PREFIX leuph: <http://leuphana.de/ontology#>
                PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                
                SELECT ?name ?title ?email ?schoolName ?instituteName
                WHERE {
                    ?person a leuph:Professor .
                    ?person leuph:name ?name .
                    OPTIONAL { ?person leuph:title ?title }
                    OPTIONAL { ?person leuph:email ?email }
                    OPTIONAL {
                        ?person leuph:worksAt|leuph:memberOf ?org .
                        ?org leuph:name ?orgName .
                        OPTIONAL {
                            { ?org a leuph:School . BIND(?orgName AS ?schoolName) }
                            UNION
                            { ?org a leuph:Institute . BIND(?orgName AS ?instituteName) }
                        }
                    }
                }
                ORDER BY ?schoolName ?name
            """
        },
        
        "institutes_in_school": {
            "description": "Which institutes belong to a specific school?",
            "query": """
                PREFIX leuph: <http://leuphana.de/ontology#>
                
                SELECT ?instituteName ?abbreviation ?description
                WHERE {
                    ?institute a leuph:Institute .
                    ?institute leuph:name ?instituteName .
                    ?institute leuph:partOf|leuph:belongsTo ?school .
                    ?school leuph:name ?schoolName .
                    FILTER(CONTAINS(LCASE(?schoolName), LCASE($school_filter)))
                    OPTIONAL { ?institute leuph:abbreviation ?abbreviation }
                    OPTIONAL { ?institute leuph:description ?description }
                }
                ORDER BY ?instituteName
            """
        },
        
        "search_person": {
            "description": "Search for a person by name",
            "query": """
                PREFIX leuph: <http://leuphana.de/ontology#>
                PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                
                SELECT ?name ?title ?email ?phone ?office ?type ?orgName
                WHERE {
                    ?person a ?type .
                    ?person leuph:name ?name .
                    FILTER(CONTAINS(LCASE(?name), LCASE($search_term)))
                    FILTER(?type IN (leuph:Professor, leuph:JuniorProfessor, 
                                     leuph:PostDoc, leuph:PhDStudent, 
                                     leuph:AcademicStaff, foaf:Person))
                    OPTIONAL { ?person leuph:title ?title }
                    OPTIONAL { ?person leuph:email ?email }
                    OPTIONAL { ?person leuph:phone ?phone }
                    OPTIONAL { ?person leuph:office ?office }
                    OPTIONAL {
                        ?person leuph:worksAt|leuph:memberOf ?org .
                        ?org leuph:name ?orgName .
                    }
                }
                ORDER BY ?name
                LIMIT 50
            """
        },
        
        "programs_by_school": {
            "description": "Which programs are offered by each school?",
            "query": """
                PREFIX leuph: <http://leuphana.de/ontology#>
                
                SELECT ?programName ?type ?duration ?language ?schoolName
                WHERE {
                    ?program a ?type .
                    ?program leuph:name ?programName .
                    FILTER(?type IN (leuph:StudyProgram, leuph:BachelorProgram, 
                                     leuph:MasterProgram, leuph:DoctoralProgram))
                    OPTIONAL { ?program leuph:duration ?duration }
                    OPTIONAL { ?program leuph:language ?language }
                    OPTIONAL {
                        ?program leuph:offeredBy ?school .
                        ?school leuph:name ?schoolName .
                    }
                }
                ORDER BY ?schoolName ?programName
            """
        },
        
        "org_hierarchy": {
            "description": "Show organizational hierarchy",
            "query": """
                PREFIX leuph: <http://leuphana.de/ontology#>
                
                SELECT ?university ?schoolName ?instituteName
                WHERE {
                    ?uni a leuph:University .
                    ?uni leuph:name ?university .
                    OPTIONAL {
                        ?school a leuph:School .
                        ?school leuph:partOf ?uni .
                        ?school leuph:name ?schoolName .
                        OPTIONAL {
                            ?institute a leuph:Institute .
                            ?institute leuph:partOf|leuph:belongsTo ?school .
                            ?institute leuph:name ?instituteName .
                        }
                    }
                }
                ORDER BY ?schoolName ?instituteName
            """
        },
        
        "staff_count": {
            "description": "Count staff by category",
            "query": """
                PREFIX leuph: <http://leuphana.de/ontology#>
                PREFIX foaf: <http://xmlns.com/foaf/0.1/>
                
                SELECT ?category (COUNT(?person) AS ?count)
                WHERE {
                    ?person a ?category .
                    FILTER(?category IN (
                        leuph:Professor, leuph:JuniorProfessor,
                        leuph:HonoraryProfessor, leuph:EmeritusProfessor,
                        leuph:PostDoc, leuph:PhDStudent,
                        leuph:ResearchAssistant, leuph:Lecturer,
                        leuph:AcademicStaff, foaf:Person
                    ))
                }
                GROUP BY ?category
                ORDER BY DESC(?count)
            """
        },
        
        "graph_stats": {
            "description": "Get knowledge graph statistics",
            "query": """
                SELECT 
                    (COUNT(DISTINCT ?s) AS ?total_subjects)
                    (COUNT(DISTINCT ?p) AS ?total_predicates)
                    (COUNT(*) AS ?total_triples)
                WHERE { ?s ?p ?o }
            """
        }
    }
    
    def __init__(self, client: GraphDBClient = None):
        """Initialize with a GraphDB client."""
        self.client = client or GraphDBClient()
    
    def list_queries(self) -> List[Dict[str, str]]:
        """List available predefined queries."""
        return [
            {"id": qid, "description": qdata["description"]}
            for qid, qdata in self.QUERIES.items()
        ]
    
    def execute(self, query_id: str, params: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Execute a predefined query.
        
        Args:
            query_id: Query identifier
            params: Optional parameters to substitute
        
        Returns:
            Query results
        """
        if query_id not in self.QUERIES:
            raise ValueError(f"Unknown query: {query_id}")
        
        query = self.QUERIES[query_id]["query"]
        
        # Substitute parameters
        if params:
            for key, value in params.items():
                query = query.replace(f"${key}", value)
        
        return self.client.query(query)
    
    def run_custom(self, sparql: str) -> Dict[str, Any]:
        """Run a custom SPARQL query."""
        return self.client.query(sparql)


# =============================================================================
# CLI Interface
# =============================================================================

def main():
    """Command-line interface for GraphDB operations."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Leuphana KG - GraphDB Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python graphdb_integration.py status           # Check connection
  python graphdb_integration.py create           # Create repository
  python graphdb_integration.py import data.ttl  # Import RDF file
  python graphdb_integration.py query all_schools # Run predefined query
  python graphdb_integration.py stats            # Show statistics
        """
    )
    
    parser.add_argument("--endpoint", help="GraphDB endpoint URL")
    parser.add_argument("--repository", "-r", help="Repository name")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # Status command
    subparsers.add_parser("status", help="Check GraphDB connection")
    
    # Create repository command
    create_parser = subparsers.add_parser("create", help="Create repository")
    create_parser.add_argument("--ruleset", default="rdfsplus-optimized",
                               help="Inference ruleset")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import RDF file")
    import_parser.add_argument("file", help="RDF file to import")
    import_parser.add_argument("--format", help="RDF format")
    import_parser.add_argument("--graph", help="Named graph URI")
    
    # Query command
    query_parser = subparsers.add_parser("query", help="Run a query")
    query_parser.add_argument("query_id", nargs="?", help="Predefined query ID")
    query_parser.add_argument("--sparql", "-s", help="Custom SPARQL query")
    query_parser.add_argument("--param", "-p", action="append", nargs=2,
                             metavar=("KEY", "VALUE"), help="Query parameter")
    
    # List queries command
    subparsers.add_parser("list", help="List predefined queries")
    
    # Statistics command
    subparsers.add_parser("stats", help="Show repository statistics")
    
    # Clear command
    subparsers.add_parser("clear", help="Clear all data from repository")
    
    args = parser.parse_args()
    
    # Create client
    client = GraphDBClient(
        endpoint=args.endpoint,
        repository=args.repository
    )
    
    if args.command == "status":
        if client.check_connection():
            print(f"✓ Connected to GraphDB at {client.endpoint}")
            repos = client.list_repositories()
            print(f"  Repositories: {', '.join(repos) or 'none'}")
        else:
            print(f"✗ Cannot connect to GraphDB at {client.endpoint}")
            print("  Make sure GraphDB is running")
            return 1
    
    elif args.command == "create":
        client.create_repository(ruleset=args.ruleset)
    
    elif args.command == "import":
        client.import_rdf(args.file, format=args.format, named_graph=args.graph)
    
    elif args.command == "query":
        runner = SPARQLQueryRunner(client)
        
        if args.sparql:
            results = runner.run_custom(args.sparql)
        elif args.query_id:
            params = dict(args.param) if args.param else {}
            results = runner.execute(args.query_id, params)
        else:
            print("Specify a query ID or use --sparql for custom query")
            return 1
        
        # Pretty print results
        bindings = results.get("results", {}).get("bindings", [])
        if bindings:
            # Print headers
            headers = list(bindings[0].keys())
            print(" | ".join(h.ljust(30) for h in headers))
            print("-" * (32 * len(headers)))
            
            # Print rows
            for row in bindings[:50]:
                values = [row.get(h, {}).get("value", "")[:30] for h in headers]
                print(" | ".join(v.ljust(30) for v in values))
            
            if len(bindings) > 50:
                print(f"... and {len(bindings) - 50} more results")
        else:
            print("No results")
    
    elif args.command == "list":
        runner = SPARQLQueryRunner(client)
        print("\nAvailable queries:")
        for q in runner.list_queries():
            print(f"  {q['id']:25} - {q['description']}")
    
    elif args.command == "stats":
        stats = client.get_statistics()
        counts = client.get_entity_counts()
        
        print("\n=== Repository Statistics ===")
        print(f"  Total triples: {stats.get('triples', 'N/A'):,}")
        print(f"  Unique subjects: {stats.get('subjects', 'N/A'):,}")
        print(f"  Unique predicates: {stats.get('predicates', 'N/A'):,}")
        
        print("\n=== Entity Counts ===")
        for entity_type, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {entity_type}: {count}")
    
    elif args.command == "clear":
        confirm = input(f"Clear all data from '{client.repository}'? [y/N] ")
        if confirm.lower() == 'y':
            client.clear_repository()
    
    else:
        parser.print_help()
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
