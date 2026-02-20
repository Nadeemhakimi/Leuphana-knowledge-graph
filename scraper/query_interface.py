#!/usr/bin/env python3
"""
Leuphana University Knowledge Graph - Query Interface

This module provides a query interface for answering questions from the KG.
Supports predefined competency queries executed via GraphDB SPARQL endpoint.

Author: Bachelor's Thesis Project
Supervisor: Debayan Banerjee
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Add parent directory to path for imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

try:
    from graphdb_integration import GraphDBClient
    GRAPHDB_AVAILABLE = True
except ImportError:
    GRAPHDB_AVAILABLE = False

try:
    from rdflib import Graph
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False


# ============================================================================
# Predefined Query Library (SPARQL for GraphDB)
# ============================================================================

SPARQL_QUERIES = {
    "professors_by_school": {
        "description": "Which professors work in which school?",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            
            SELECT ?name ?type ?affiliation
            WHERE {
                { ?p a leuph:Professor } UNION { ?p a leuph:AcademicStaff }
                ?p foaf:name ?name .
                ?p a ?type .
                OPTIONAL {
                    ?p leuph:worksAt ?org .
                    ?org leuph:name ?affiliation .
                }
                FILTER(?type IN (leuph:Professor, leuph:JuniorProfessor, 
                                 leuph:AcademicStaff, leuph:PostDoc))
            }
            ORDER BY ?name
            LIMIT 100
        """,
        "params": {}
    },

    "professors_in_school": {
        "description": "Find professors in a specific school",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            
            SELECT ?name ?email ?organization
            WHERE {
                ?p a leuph:Professor .
                ?p foaf:name ?name .
                ?p leuph:worksAt ?org .
                ?org leuph:name ?organization .
                OPTIONAL { ?p leuph:email ?email }
                FILTER(CONTAINS(LCASE(?organization), LCASE("$school_name")))
            }
            ORDER BY ?name
        """,
        "params": {"school_name": ""}
    },

    "institutes_by_school": {
        "description": "Which institutes belong to which school?",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            
            SELECT ?school (GROUP_CONCAT(?instituteName; separator=", ") AS ?institutes)
            WHERE {
                ?i a leuph:Institute .
                ?i leuph:name ?instituteName .
                ?i leuph:partOf ?s .
                ?s a leuph:School .
                ?s leuph:name ?school .
            }
            GROUP BY ?school
            ORDER BY ?school
        """,
        "params": {}
    },

    "all_schools": {
        "description": "List all schools/faculties",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            
            SELECT ?school ?description (COUNT(DISTINCT ?i) AS ?institute_count)
            WHERE {
                ?s a leuph:School .
                ?s leuph:name ?school .
                OPTIONAL { ?s leuph:description ?description }
                OPTIONAL {
                    ?i a leuph:Institute .
                    ?i leuph:partOf ?s .
                }
            }
            GROUP BY ?school ?description
            ORDER BY ?school
        """,
        "params": {}
    },

    "all_institutes": {
        "description": "List all institutes",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            
            SELECT ?institute ?school ?abbreviation
            WHERE {
                ?i a leuph:Institute .
                ?i leuph:name ?institute .
                OPTIONAL { ?i leuph:abbreviation ?abbreviation }
                OPTIONAL {
                    ?i leuph:partOf ?s .
                    ?s leuph:name ?school .
                }
            }
            ORDER BY ?school ?institute
        """,
        "params": {}
    },

    "all_chairs": {
        "description": "List all chairs/professorships",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            
            SELECT ?chair ?headName ?institute
            WHERE {
                ?c a leuph:Chair .
                ?c leuph:name ?chair .
                OPTIONAL {
                    ?c leuph:headedBy ?head .
                    ?head foaf:name ?headName .
                }
                OPTIONAL {
                    ?c leuph:partOf ?i .
                    ?i leuph:name ?institute .
                }
            }
            ORDER BY ?chair
        """,
        "params": {}
    },

    "hiwi_positions": {
        "description": "List available Hiwi/student assistant positions",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            
            SELECT ?title ?hours ?postedDate ?department
            WHERE {
                ?pos a leuph:HiwiPosition .
                ?pos leuph:name ?title .
                OPTIONAL { ?pos leuph:hoursPerWeek ?hours }
                OPTIONAL { ?pos leuph:postedDate ?postedDate }
                OPTIONAL {
                    ?pos leuph:postedBy ?dept .
                    ?dept leuph:name ?department .
                }
            }
            ORDER BY DESC(?postedDate)
        """,
        "params": {}
    },

    "search_person": {
        "description": "Search for a person by name",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            
            SELECT ?name ?type ?email ?phone ?organization
            WHERE {
                ?p foaf:name ?name .
                ?p a ?type .
                FILTER(CONTAINS(LCASE(?name), LCASE("$search_term")))
                FILTER(?type IN (leuph:Professor, leuph:JuniorProfessor, 
                                 leuph:AcademicStaff, leuph:PostDoc, 
                                 leuph:PhDStudent, foaf:Person))
                OPTIONAL { ?p leuph:email ?email }
                OPTIONAL { ?p leuph:phone ?phone }
                OPTIONAL {
                    ?p leuph:worksAt ?org .
                    ?org leuph:name ?organization .
                }
            }
            ORDER BY ?name
            LIMIT 20
        """,
        "params": {"search_term": ""}
    },

    "programs_by_school": {
        "description": "List study programs by school",
        "query": """
            PREFIX leuph: <http://leuphana.de/ontology#>
            
            SELECT ?school ?programType ?programName
            WHERE {
                ?prog leuph:name ?programName .
                ?prog a ?programType .
                ?prog leuph:offeredBy ?s .
                ?s leuph:name ?school .
                FILTER(?programType IN (leuph:BachelorProgram, leuph:MasterProgram))
            }
            ORDER BY ?school ?programType ?programName
        """,
        "params": {}
    },

    "graph_stats": {
        "description": "Get knowledge graph statistics",
        "query": """
            SELECT 
                (COUNT(DISTINCT ?s) AS ?subjects)
                (COUNT(DISTINCT ?p) AS ?predicates)
                (COUNT(*) AS ?triples)
            WHERE { ?s ?p ?o }
        """,
        "params": {}
    }
}


# ============================================================================
# Query Result Handler
# ============================================================================

class QueryResult:
    """Wrapper for query results with formatting."""

    def __init__(self, query_id: str, bindings: List[Dict], count: int = None):
        self.query_id = query_id
        self.bindings = bindings
        self.count = count or len(bindings)

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "query": self.query_id,
            "count": self.count,
            "results": self.bindings
        }

    def to_table(self) -> str:
        """Format as ASCII table."""
        if not self.bindings:
            return "No results found."

        # Get headers from first result
        headers = list(self.bindings[0].keys())

        # Calculate column widths
        widths = {h: len(h) for h in headers}
        for row in self.bindings[:50]:  # Limit for display
            for h in headers:
                val = str(row.get(h, {}).get("value", ""))[:50]
                widths[h] = max(widths[h], len(val))

        # Build table
        lines = []
        header_line = " | ".join(h.ljust(widths[h]) for h in headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))

        for row in self.bindings[:50]:
            values = [str(row.get(h, {}).get("value", ""))[:50].ljust(widths[h]) for h in headers]
            lines.append(" | ".join(values))

        if self.count > 50:
            lines.append(f"... and {self.count - 50} more results")

        return "\n".join(lines)


# ============================================================================
# Query Handler (GraphDB)
# ============================================================================

class PredefinedQueryHandler:
    """Handles execution of predefined competency queries via GraphDB."""

    def __init__(self, graphdb_endpoint: str = None, graphdb_repository: str = None):
        """
        Initialize query handler with GraphDB connection.

        Args:
            graphdb_endpoint: GraphDB endpoint URL (default from env)
            graphdb_repository: GraphDB repository name (default from env)
        """
        self.endpoint = graphdb_endpoint or os.getenv("GRAPHDB_ENDPOINT", "http://localhost:7200")
        self.repository = graphdb_repository or os.getenv("GRAPHDB_REPOSITORY", "leuphana-kg")
        self.client = None

        if GRAPHDB_AVAILABLE:
            try:
                self.client = GraphDBClient(
                    endpoint=self.endpoint,
                    repository=self.repository
                )
                # Test connection
                if self.client.check_connection():
                    print(f"Connected to GraphDB at {self.endpoint}")
                else:
                    print(f"Warning: Could not connect to GraphDB at {self.endpoint}")
                    self.client = None
            except Exception as e:
                print(f"Warning: Could not connect to GraphDB: {e}")
                self.client = None

    def close(self):
        """Close the GraphDB connection."""
        # GraphDB client doesn't need explicit close
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def list_queries(self) -> List[Dict]:
        """List all available predefined queries."""
        return [
            {"id": qid, "description": qdata["description"]}
            for qid, qdata in SPARQL_QUERIES.items()
        ]

    def get_query_info(self, query_id: str) -> Optional[Dict]:
        """Get information about a specific query."""
        if query_id in SPARQL_QUERIES:
            qdata = SPARQL_QUERIES[query_id]
            return {
                "id": query_id,
                "description": qdata["description"],
                "required_params": [k for k, v in qdata["params"].items() if v == ""]
            }
        return None

    def execute(self, query_id: str, params: Dict = None) -> QueryResult:
        """
        Execute a predefined query.

        Args:
            query_id: ID of the query to execute
            params: Parameters to pass to the query

        Returns:
            QueryResult object with results
        """
        if query_id not in SPARQL_QUERIES:
            raise ValueError(f"Unknown query: {query_id}. Use list_queries() to see available queries.")

        if not self.client:
            raise RuntimeError("No GraphDB connection. Check your configuration.")

        qdata = SPARQL_QUERIES[query_id]
        query = qdata["query"]

        # Substitute parameters
        if params:
            for key, value in params.items():
                query = query.replace(f"${key}", value)

        # Execute query
        results = self.client.query(query)
        bindings = results.get("results", {}).get("bindings", [])

        return QueryResult(query_id, bindings)

    def execute_sparql(self, sparql: str) -> QueryResult:
        """Execute a custom SPARQL query."""
        if not self.client:
            raise RuntimeError("No GraphDB connection. Check your configuration.")

        results = self.client.query(sparql)
        bindings = results.get("results", {}).get("bindings", [])

        return QueryResult("custom", bindings)


# ============================================================================
# Interactive Mode
# ============================================================================

def interactive_mode(handler: PredefinedQueryHandler):
    """Run an interactive query session."""
    print("\n" + "=" * 60)
    print("  Leuphana KG - Interactive Query Mode")
    print("=" * 60)
    print("\nCommands:")
    print("  list              - Show available queries")
    print("  run <query_id>    - Execute a query")
    print("  sparql            - Enter custom SPARQL")
    print("  help              - Show this help")
    print("  quit              - Exit")
    print()

    while True:
        try:
            cmd = input("leuphana-kg> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        action = parts[0].lower()

        if action in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        elif action == "list":
            print("\nAvailable queries:")
            for q in handler.list_queries():
                print(f"  {q['id']:25} - {q['description']}")
            print()

        elif action == "run":
            if len(parts) < 2:
                print("Usage: run <query_id> [param=value ...]")
                continue

            query_parts = parts[1].split()
            query_id = query_parts[0]

            # Parse parameters
            params = {}
            for p in query_parts[1:]:
                if "=" in p:
                    key, value = p.split("=", 1)
                    params[key] = value

            try:
                info = handler.get_query_info(query_id)
                if info and info["required_params"]:
                    for req in info["required_params"]:
                        if req not in params:
                            params[req] = input(f"  Enter {req}: ")

                result = handler.execute(query_id, params)
                print(f"\n{result.to_table()}\n")
            except Exception as e:
                print(f"Error: {e}")

        elif action == "sparql":
            print("Enter SPARQL query (end with semicolon on new line):")
            lines = []
            while True:
                line = input("  ")
                if line.strip() == ";":
                    break
                lines.append(line)

            sparql = "\n".join(lines)
            try:
                result = handler.execute_sparql(sparql)
                print(f"\n{result.to_table()}\n")
            except Exception as e:
                print(f"Error: {e}")

        elif action == "help":
            print("\nCommands:")
            print("  list              - Show available queries")
            print("  run <query_id>    - Execute a query")
            print("  sparql            - Enter custom SPARQL")
            print("  help              - Show this help")
            print("  quit              - Exit")
            print()

        else:
            print(f"Unknown command: {action}. Type 'help' for available commands.")


# ============================================================================
# CLI
# ============================================================================

def main():
    """Command-line interface."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Leuphana KG Query Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python query_interface.py list
  python query_interface.py run all_schools
  python query_interface.py run search_person search_term=Schmidt
  python query_interface.py interactive
        """
    )

    parser.add_argument("--endpoint", help="GraphDB endpoint URL")
    parser.add_argument("--repository", "-r", help="GraphDB repository name")

    subparsers = parser.add_subparsers(dest="command")

    # List command
    subparsers.add_parser("list", help="List available queries")

    # Run command
    run_parser = subparsers.add_parser("run", help="Execute a query")
    run_parser.add_argument("query_id", help="Query ID to execute")
    run_parser.add_argument("params", nargs="*", help="Parameters (key=value)")

    # Interactive command
    subparsers.add_parser("interactive", help="Start interactive mode")

    args = parser.parse_args()

    # Create handler
    try:
        handler = PredefinedQueryHandler(
            graphdb_endpoint=args.endpoint,
            graphdb_repository=args.repository
        )
    except Exception as e:
        print(f"Error connecting to GraphDB: {e}")
        print("\nMake sure GraphDB is running and credentials are set in .env file")
        return 1

    if args.command == "list":
        print("\nAvailable queries:")
        for q in handler.list_queries():
            print(f"  {q['id']:25} - {q['description']}")

    elif args.command == "run":
        # Parse parameters
        params = {}
        for p in args.params or []:
            if "=" in p:
                key, value = p.split("=", 1)
                params[key] = value

        try:
            result = handler.execute(args.query_id, params)
            print(result.to_table())
        except Exception as e:
            print(f"Error: {e}")
            return 1

    elif args.command == "interactive":
        interactive_mode(handler)

    else:
        parser.print_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())