#!/usr/bin/env python3
"""
Leuphana University Knowledge Graph - Visualization Helpers

This module provides utilities for visualizing the knowledge graph
using various tools and formats.

Author: Bachelor's Thesis Project
Supervisor: Debayan Banerjee
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF, RDFS
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import networkx as nx
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# =============================================================================
# D3.js JSON Format Export
# =============================================================================

def rdf_to_d3_json(rdf_file: str, output_file: str):
    """
    Convert RDF graph to D3.js force-directed graph JSON format.

    Args:
        rdf_file: Input RDF file (Turtle format)
        output_file: Output JSON file for D3.js
    """
    if not RDFLIB_AVAILABLE:
        print("Error: rdflib required. Install with: pip install rdflib")
        return

    g = Graph()
    g.parse(rdf_file, format="turtle")

    nodes = {}
    links = []

    LEUPH = Namespace("http://leuphana.de/ontology#")
    FOAF = Namespace("http://xmlns.com/foaf/0.1/")
    SCHEMA = Namespace("http://schema.org/")

    def get_literal(subject, predicates):
        """Get first matching literal value from a list of predicates."""
        for pred in predicates:
            values = list(g.objects(subject, pred))
            if values:
                return str(values[0])
        return None

    # Extract nodes
    for s, p, o in g:
        # Subject as node
        s_str = str(s)
        if s_str not in nodes:
            # Determine node type
            types = list(g.objects(s, RDF.type))
            type_label = str(types[0]).split('#')[-1].split('/')[-1] if types else "Unknown"
            name = get_literal(s, [LEUPH.name, FOAF.name, RDFS.label]) or s_str.split('/')[-1]

            # Extract additional properties
            node_data = {
                "id": s_str,
                "name": name,
                "type": type_label,
                "group": _get_group_number(type_label)
            }

            # Add optional properties if they exist
            email = get_literal(s, [LEUPH.email, FOAF.mbox, SCHEMA.email])
            if email:
                node_data["email"] = email.replace("mailto:", "")

            title = get_literal(s, [LEUPH.title, LEUPH.academicTitle, SCHEMA.jobTitle])
            if title:
                node_data["title"] = title

            description = get_literal(s, [LEUPH.description, RDFS.comment, SCHEMA.description])
            if description:
                node_data["description"] = description[:200] + "..." if len(description) > 200 else description

            url = get_literal(s, [LEUPH.url, LEUPH.profileUrl, SCHEMA.url])
            if url:
                node_data["url"] = url

            phone = get_literal(s, [LEUPH.phone, FOAF.phone, SCHEMA.telephone])
            if phone:
                node_data["phone"] = phone

            office = get_literal(s, [LEUPH.office, LEUPH.location])
            if office:
                node_data["office"] = office

            abbreviation = get_literal(s, [LEUPH.abbreviation])
            if abbreviation:
                node_data["abbreviation"] = abbreviation

            nodes[s_str] = node_data

        # Object as node (if it's a URI from our resource namespace, not external URLs)
        # Only include URIs from http://leuphana.de/resource/ - skip external URLs like webpage links
        if hasattr(o, 'startswith') and str(o).startswith('http://leuphana.de/resource/'):
            o_str = str(o)
            if o_str not in nodes:
                types = list(g.objects(o, RDF.type))
                type_label = str(types[0]).split('#')[-1].split('/')[-1] if types else "Unknown"
                name = get_literal(o, [LEUPH.name, FOAF.name, RDFS.label]) or o_str.split('/')[-1]

                node_data = {
                    "id": o_str,
                    "name": name,
                    "type": type_label,
                    "group": _get_group_number(type_label)
                }

                # Add optional properties for object nodes too
                email = get_literal(o, [LEUPH.email, FOAF.mbox, SCHEMA.email])
                if email:
                    node_data["email"] = email.replace("mailto:", "")

                title = get_literal(o, [LEUPH.title, LEUPH.academicTitle, SCHEMA.jobTitle])
                if title:
                    node_data["title"] = title

                description = get_literal(o, [LEUPH.description, RDFS.comment, SCHEMA.description])
                if description:
                    node_data["description"] = description[:200] + "..." if len(description) > 200 else description

                url = get_literal(o, [LEUPH.url, LEUPH.profileUrl, SCHEMA.url])
                if url:
                    node_data["url"] = url

                abbreviation = get_literal(o, [LEUPH.abbreviation])
                if abbreviation:
                    node_data["abbreviation"] = abbreviation

                nodes[o_str] = node_data

            # Add link only for entity-to-entity relationships (both must be resource URIs)
            p_str = str(p).split('#')[-1].split('/')[-1]
            links.append({
                "source": s_str,
                "target": o_str,
                "type": p_str
            })

    # Create D3 JSON structure
    d3_data = {
        "nodes": list(nodes.values()),
        "links": links
    }

    with open(output_file, 'w') as f:
        json.dump(d3_data, f, indent=2)

    print(f"Exported {len(nodes)} nodes and {len(links)} links to {output_file}")


def _get_group_number(type_label: str) -> int:
    """Map entity types to group numbers for D3 visualization."""
    groups = {
        # Organizational structure
        "University": 1,
        "School": 2,
        "Institute": 3,
        "Chair": 3,  # Chair (Lehrstuhl) same as institute
        "ResearchCenter": 3,
        "ResearchGroup": 3,
        # People
        "Professor": 4,
        "JuniorProfessor": 4,
        "HonoraryProfessor": 4,
        "EmeritusProfessor": 4,
        "VisitingProfessor": 4,
        "AdjunctProfessor": 4,
        "ResearchAssistant": 5,
        "PostDoc": 5,
        "PhDStudent": 5,
        "Lecturer": 5,
        "VisitingScientist": 5,
        "AcademicStaff": 5,
        "AdministrativeStaff": 5,
        "StudentAssistant": 5,
        "Person": 5,
        # Programs and courses
        "StudyProgram": 6,
        "BachelorProgram": 6,
        "MasterProgram": 6,
        "DoctoralProgram": 6,
        "Minor": 6,
        "Course": 7,
        "Module": 7,
        # Positions
        "HiWiPosition": 8,
        "HiwiPosition": 8,
        "JobPosition": 8,
        # Research
        "ResearchProject": 9,
    }
    return groups.get(type_label, 0)


# =============================================================================
# Graphviz DOT Format Export
# =============================================================================

def rdf_to_dot(rdf_file: str, output_file: str, max_nodes: int = 100):
    """
    Convert RDF graph to Graphviz DOT format.
    
    Args:
        rdf_file: Input RDF file
        output_file: Output DOT file
        max_nodes: Maximum number of nodes to include
    """
    if not RDFLIB_AVAILABLE:
        print("Error: rdflib required")
        return
    
    g = Graph()
    g.parse(rdf_file, format="turtle")
    
    LEUPH = Namespace("http://leuphana.de/ontology#")
    
    # Color mapping for node types
    colors = {
        "University": "#1f77b4",
        "School": "#ff7f0e",
        "Institute": "#2ca02c",
        "Professor": "#d62728",
        "JuniorProfessor": "#d62728",
        "ResearchAssistant": "#9467bd",
        "PostDoc": "#9467bd",
        "PhDStudent": "#8c564b",
        "StudyProgram": "#e377c2",
        "BachelorProgram": "#e377c2",
        "MasterProgram": "#e377c2",
    }
    
    dot_lines = [
        "digraph LeuphanaKG {",
        "  rankdir=TB;",
        "  node [shape=box, style=filled];",
        "  edge [fontsize=10];",
        ""
    ]
    
    nodes_added = set()
    edges_added = set()
    
    for s, p, o in g:
        if len(nodes_added) >= max_nodes:
            break
        
        s_str = str(s)
        
        if s_str not in nodes_added:
            types = list(g.objects(s, RDF.type))
            type_label = str(types[0]).split('#')[-1].split('/')[-1] if types else "Unknown"
            names = list(g.objects(s, LEUPH.name))
            name = str(names[0]) if names else s_str.split('/')[-1]
            color = colors.get(type_label, "#cccccc")
            
            # Escape special characters
            name = name.replace('"', '\\"').replace('\n', ' ')[:50]
            node_id = s_str.replace('/', '_').replace(':', '_').replace('#', '_').replace('.', '_')
            
            dot_lines.append(f'  "{node_id}" [label="{name}\\n({type_label})", fillcolor="{color}"];')
            nodes_added.add(s_str)
        
        # Add object node and edge if it's a URI
        if hasattr(o, 'startswith') and str(o).startswith('http'):
            o_str = str(o)
            
            if o_str not in nodes_added and len(nodes_added) < max_nodes:
                types = list(g.objects(o, RDF.type))
                type_label = str(types[0]).split('#')[-1].split('/')[-1] if types else "Unknown"
                names = list(g.objects(o, LEUPH.name))
                name = str(names[0]) if names else o_str.split('/')[-1]
                color = colors.get(type_label, "#cccccc")
                
                name = name.replace('"', '\\"').replace('\n', ' ')[:50]
                node_id = o_str.replace('/', '_').replace(':', '_').replace('#', '_').replace('.', '_')
                
                dot_lines.append(f'  "{node_id}" [label="{name}\\n({type_label})", fillcolor="{color}"];')
                nodes_added.add(o_str)
            
            # Add edge
            p_label = str(p).split('#')[-1].split('/')[-1]
            edge_key = (s_str, o_str, p_label)
            
            if edge_key not in edges_added and o_str in nodes_added:
                s_id = s_str.replace('/', '_').replace(':', '_').replace('#', '_').replace('.', '_')
                o_id = o_str.replace('/', '_').replace(':', '_').replace('#', '_').replace('.', '_')
                dot_lines.append(f'  "{s_id}" -> "{o_id}" [label="{p_label}"];')
                edges_added.add(edge_key)
    
    dot_lines.append("}")
    
    with open(output_file, 'w') as f:
        f.write('\n'.join(dot_lines))
    
    print(f"Exported DOT file with {len(nodes_added)} nodes to {output_file}")
    print(f"Generate image with: dot -Tpng {output_file} -o output.png")


# =============================================================================
# GraphDB SPARQL Queries (for visualization)
# =============================================================================

def generate_graphdb_viz_query(entity_type: str = "School") -> str:
    """
    Generate SPARQL queries optimized for GraphDB visualization.
    
    Args:
        entity_type: Type of entity to visualize
    
    Returns:
        SPARQL query string
    """
    queries = {
        "School": """
            # Visualize Schools and their Institutes
            PREFIX leuph: <http://leuphana.de/ontology#>
            
            SELECT ?university ?school ?institute
            WHERE {
                ?university a leuph:University .
                ?school a leuph:School .
                ?school leuph:partOf ?university .
                OPTIONAL {
                    ?institute a leuph:Institute .
                    ?institute leuph:partOf ?school .
                }
            }
            LIMIT 100
        """,
        "Professor": """
            # Visualize Professors and their affiliations
            PREFIX leuph: <http://leuphana.de/ontology#>
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            
            SELECT ?professor ?name ?organization
            WHERE {
                ?professor a leuph:Professor .
                ?professor foaf:name ?name .
                ?professor leuph:worksAt ?organization .
            }
            LIMIT 100
        """,
        "Hierarchy": """
            # Visualize complete organizational hierarchy
            PREFIX leuph: <http://leuphana.de/ontology#>
            
            SELECT ?parent ?child ?parentName ?childName
            WHERE {
                ?child leuph:partOf ?parent .
                ?parent leuph:name ?parentName .
                ?child leuph:name ?childName .
            }
            LIMIT 200
        """,
        "Programs": """
            # Visualize Study Programs and their offerings
            PREFIX leuph: <http://leuphana.de/ontology#>
            
            SELECT ?program ?programName ?school ?schoolName
            WHERE {
                { ?program a leuph:BachelorProgram } UNION { ?program a leuph:MasterProgram }
                ?program leuph:name ?programName .
                ?program leuph:offeredBy ?school .
                ?school leuph:name ?schoolName .
            }
            LIMIT 100
        """
    }
    
    return queries.get(entity_type, queries["School"])


# =============================================================================
# HTML Visualization Generator
# =============================================================================

def generate_html_visualization(json_file: str, output_file: str):
    """
    Generate an interactive HTML visualization using D3.js.

    Args:
        json_file: D3 JSON data file
        output_file: Output HTML file
    """
    html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Leuphana Knowledge Graph Visualization</title>
    <style>
        * { box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 0; background: #f5f5f5; }
        #graph { width: 100vw; height: 100vh; background: #ffffff; }
        .node { cursor: pointer; }
        .node text { font-size: 10px; pointer-events: none; fill: #333; }
        .node circle { stroke: #fff; stroke-width: 2px; }
        .node:hover circle { stroke: #333; stroke-width: 3px; }
        .link { stroke: #999; stroke-opacity: 0.4; }
        .tooltip {
            position: absolute; background: white; border: 1px solid #ddd;
            padding: 12px 16px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            display: none; max-width: 350px; font-size: 13px; line-height: 1.5; z-index: 1000;
        }
        .tooltip-title { font-weight: bold; font-size: 15px; margin-bottom: 8px; border-bottom: 1px solid #eee; padding-bottom: 6px; }
        .tooltip-type { display: inline-block; background: #e0e0e0; padding: 2px 8px; border-radius: 12px; font-size: 11px; margin-bottom: 8px; }
        .tooltip-row { margin: 4px 0; color: #555; }
        .tooltip-row strong { color: #333; }
        .tooltip-row a { color: #1976d2; text-decoration: none; }
        .tooltip-description { margin-top: 8px; padding-top: 8px; border-top: 1px solid #eee; color: #666; font-size: 12px; }
        .legend { position: fixed; top: 10px; right: 10px; background: white; padding: 15px; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); max-height: 80vh; overflow-y: auto; z-index: 100; }
        .legend h4 { margin: 0 0 12px 0; font-size: 14px; border-bottom: 1px solid #eee; padding-bottom: 8px; }
        .legend-item { display: flex; align-items: center; margin: 6px 0; cursor: pointer; padding: 4px 8px; border-radius: 4px; }
        .legend-item:hover { background: #f5f5f5; }
        .legend-item.dimmed { opacity: 0.4; }
        .legend-color { width: 16px; height: 16px; margin-right: 10px; border-radius: 50%; }
        .legend-label { font-size: 13px; }
        .legend-count { margin-left: auto; font-size: 11px; color: #888; background: #f0f0f0; padding: 2px 6px; border-radius: 10px; }
        .controls { position: fixed; top: 10px; left: 10px; background: white; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); z-index: 100; }
        .controls input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; width: 200px; font-size: 13px; }
        .controls input:focus { outline: none; border-color: #1976d2; }
        .stats { position: fixed; bottom: 10px; left: 10px; background: white; padding: 10px 15px; border: 1px solid #ddd; border-radius: 8px; font-size: 12px; color: #666; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div id="graph"></div>
    <div class="tooltip" id="tooltip"></div>
    <div class="legend" id="legend"><h4>Entity Types</h4><div id="legend-items"></div></div>
    <div class="controls"><input type="text" id="search" placeholder="Search nodes..."></div>
    <div class="stats" id="stats"></div>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <script>
        const colorPalette = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"];
        const typePriority = { "University": 100, "School": 90, "Institute": 80, "Professor": 70, "JuniorProfessor": 65, "PostDoc": 60, "AcademicStaff": 45, "MasterProgram": 35, "BachelorProgram": 30 };
        const width = window.innerWidth, height = window.innerHeight;
        const svg = d3.select("#graph").append("svg").attr("width", width).attr("height", height);
        const g = svg.append("g");
        svg.call(d3.zoom().scaleExtent([0.1, 4]).on("zoom", (event) => g.attr("transform", event.transform)));

        d3.json("''' + json_file + '''").then(data => {
            const typeSet = new Set(); data.nodes.forEach(n => { if (n.type && n.type !== "Unknown") typeSet.add(n.type); });
            const sortedTypes = Array.from(typeSet).sort((a, b) => (typePriority[b] || 0) - (typePriority[a] || 0));
            const typeColors = {}; sortedTypes.forEach((t, i) => { typeColors[t] = colorPalette[i % colorPalette.length]; }); typeColors["Unknown"] = "#ccc";
            const typeCounts = {}; data.nodes.forEach(n => { const t = n.type || "Unknown"; typeCounts[t] = (typeCounts[t] || 0) + 1; });

            const legendContainer = d3.select("#legend-items");
            const activeTypes = new Set(sortedTypes);
            sortedTypes.forEach(type => {
                const item = legendContainer.append("div").attr("class", "legend-item").on("click", function() {
                    if (activeTypes.has(type)) { activeTypes.delete(type); d3.select(this).classed("dimmed", true); }
                    else { activeTypes.add(type); d3.select(this).classed("dimmed", false); }
                    updateVisibility();
                });
                item.append("div").attr("class", "legend-color").style("background", typeColors[type]);
                item.append("span").attr("class", "legend-label").text(type);
                item.append("span").attr("class", "legend-count").text(typeCounts[type] || 0);
            });

            d3.select("#stats").html(`<strong>${data.nodes.length}</strong> nodes | <strong>${data.links.length}</strong> relationships`);

            const simulation = d3.forceSimulation(data.nodes)
                .force("link", d3.forceLink(data.links).id(d => d.id).distance(100))
                .force("charge", d3.forceManyBody().strength(-300))
                .force("center", d3.forceCenter(width / 2, height / 2))
                .force("collision", d3.forceCollide().radius(30));

            const link = g.append("g").selectAll("line").data(data.links).join("line").attr("class", "link");
            const node = g.append("g").selectAll("g").data(data.nodes).join("g").attr("class", "node")
                .call(d3.drag().on("start", dragstarted).on("drag", dragged).on("end", dragended));

            function getNodeSize(d) { const sizes = { "University": 25, "School": 18, "Institute": 14, "Professor": 10 }; return sizes[d.type] || 8; }
            node.append("circle").attr("r", d => getNodeSize(d)).attr("fill", d => typeColors[d.type] || "#ccc");
            node.append("text").text(d => d.name ? d.name.substring(0, 20) : "").attr("x", d => getNodeSize(d) + 4).attr("y", 4);

            const tooltip = d3.select("#tooltip");
            node.on("mouseover", (event, d) => {
                let html = `<div class="tooltip-title">${d.name || "Unknown"}</div><span class="tooltip-type" style="background:${typeColors[d.type] || "#ccc"}">${d.type || "Unknown"}</span>`;
                if (d.title) html += `<div class="tooltip-row"><strong>Title:</strong> ${d.title}</div>`;
                if (d.abbreviation) html += `<div class="tooltip-row"><strong>Abbr:</strong> ${d.abbreviation}</div>`;
                if (d.email) html += `<div class="tooltip-row"><strong>Email:</strong> <a href="mailto:${d.email}">${d.email}</a></div>`;
                if (d.phone) html += `<div class="tooltip-row"><strong>Phone:</strong> ${d.phone}</div>`;
                if (d.office) html += `<div class="tooltip-row"><strong>Office:</strong> ${d.office}</div>`;
                if (d.url) html += `<div class="tooltip-row"><strong>Profile:</strong> <a href="${d.url}" target="_blank">View</a></div>`;
                if (d.description) html += `<div class="tooltip-description">${d.description}</div>`;
                const connections = data.links.filter(l => l.source.id === d.id || l.target.id === d.id || l.source === d.id || l.target === d.id).length;
                html += `<div class="tooltip-row"><strong>Connections:</strong> ${connections}</div>`;
                tooltip.style("display", "block").html(html).style("left", (event.pageX + 15) + "px").style("top", (event.pageY + 15) + "px");
            }).on("mouseout", () => tooltip.style("display", "none")).on("click", (e, d) => { if (d.url) window.open(d.url, "_blank"); });

            function updateVisibility() {
                node.style("opacity", d => activeTypes.has(d.type) ? 1 : 0.1);
                link.style("opacity", d => { const st = typeof d.source === 'object' ? d.source.type : data.nodes.find(n => n.id === d.source)?.type;
                    const tt = typeof d.target === 'object' ? d.target.type : data.nodes.find(n => n.id === d.target)?.type;
                    return (activeTypes.has(st) && activeTypes.has(tt)) ? 0.4 : 0.05; });
            }

            d3.select("#search").on("input", function() {
                const term = this.value.toLowerCase();
                node.style("opacity", d => term.length === 0 ? (activeTypes.has(d.type) ? 1 : 0.1) :
                    ((d.name || "").toLowerCase().includes(term) || (d.type || "").toLowerCase().includes(term)) ? 1 : 0.1);
            });

            simulation.on("tick", () => {
                link.attr("x1", d => d.source.x).attr("y1", d => d.source.y).attr("x2", d => d.target.x).attr("y2", d => d.target.y);
                node.attr("transform", d => `translate(${d.x},${d.y})`);
            });

            function dragstarted(event) { if (!event.active) simulation.alphaTarget(0.3).restart(); event.subject.fx = event.subject.x; event.subject.fy = event.subject.y; }
            function dragged(event) { event.subject.fx = event.x; event.subject.fy = event.y; }
            function dragended(event) { if (!event.active) simulation.alphaTarget(0); event.subject.fx = null; event.subject.fy = null; }
        }).catch(err => d3.select("#stats").html(`<span style="color:red">Error: ${err.message}</span>`));
    </script>
</body>
</html>'''

    with open(output_file, 'w') as f:
        f.write(html_template)

    print(f"Generated HTML visualization: {output_file}")
    print(f"Note: Make sure {json_file} is in the same directory or update the path")


# =============================================================================
# Python Native Visualization (matplotlib + networkx)
# =============================================================================

def visualize_kg_matplotlib(
    rdf_file: str,
    output_file: str = None,
    filter_types: List[str] = None,
    max_nodes: int = 100,
    figsize: tuple = (16, 12),
    show: bool = True
):
    """
    Visualize the knowledge graph using matplotlib and networkx.

    Args:
        rdf_file: Input RDF file (Turtle format)
        output_file: Optional output image file (PNG, PDF, SVG)
        filter_types: List of entity types to include (None = all)
        max_nodes: Maximum number of nodes to display
        figsize: Figure size tuple (width, height)
        show: Whether to display the plot interactively
    """
    if not RDFLIB_AVAILABLE:
        print("Error: rdflib required. Install with: pip install rdflib")
        return
    if not MATPLOTLIB_AVAILABLE:
        print("Error: matplotlib and networkx required.")
        print("Install with: pip install matplotlib networkx")
        return

    g = Graph()
    g.parse(rdf_file, format="turtle")

    LEUPH = Namespace("http://leuphana.de/ontology#")

    # Color mapping for node types
    colors = {
        "University": "#1f77b4",
        "School": "#ff7f0e",
        "Institute": "#2ca02c",
        "Professor": "#d62728",
        "JuniorProfessor": "#d62728",
        "AcademicStaff": "#9467bd",
        "ResearchAssistant": "#9467bd",
        "PostDoc": "#9467bd",
        "PhDStudent": "#8c564b",
        "Person": "#17becf",
        "StudyProgram": "#e377c2",
        "BachelorProgram": "#e377c2",
        "MasterProgram": "#e377c2",
        "ResearchCenter": "#bcbd22",
    }

    # Size mapping for node types
    sizes = {
        "University": 2000,
        "School": 1200,
        "Institute": 800,
        "Professor": 400,
        "Person": 300,
        "AcademicStaff": 300,
    }

    # Build networkx graph
    G = nx.DiGraph()
    node_colors = []
    node_sizes = []
    node_labels = {}

    # Important relationship types for visualization
    important_rels = {'partOf', 'belongsTo', 'memberOf', 'worksAt', 'hasPart', 'hasEmployee', 'hasMember'}

    nodes_added = set()

    for s, p, o in g:
        # Only include object property relationships (URIs, not literals)
        if not (hasattr(o, 'startswith') and str(o).startswith('http')):
            continue

        # Filter by relationship type
        p_name = str(p).split('#')[-1].split('/')[-1]
        if p_name not in important_rels:
            continue

        s_str = str(s)
        o_str = str(o)

        # Get node info for subject
        if s_str not in nodes_added and len(nodes_added) < max_nodes:
            types = list(g.objects(s, RDF.type))
            type_label = str(types[0]).split('#')[-1].split('/')[-1] if types else "Unknown"

            if filter_types and type_label not in filter_types:
                continue

            names = list(g.objects(s, LEUPH.name))
            name = str(names[0])[:25] if names else s_str.split('/')[-1][:25]

            G.add_node(s_str, label=name, type=type_label)
            node_colors.append(colors.get(type_label, "#cccccc"))
            node_sizes.append(sizes.get(type_label, 300))
            node_labels[s_str] = name
            nodes_added.add(s_str)

        # Get node info for object
        if o_str not in nodes_added and len(nodes_added) < max_nodes:
            types = list(g.objects(o, RDF.type))
            type_label = str(types[0]).split('#')[-1].split('/')[-1] if types else "Unknown"

            if filter_types and type_label not in filter_types:
                continue

            names = list(g.objects(o, LEUPH.name))
            name = str(names[0])[:25] if names else o_str.split('/')[-1][:25]

            G.add_node(o_str, label=name, type=type_label)
            node_colors.append(colors.get(type_label, "#cccccc"))
            node_sizes.append(sizes.get(type_label, 300))
            node_labels[o_str] = name
            nodes_added.add(o_str)

        # Add edge
        if s_str in nodes_added and o_str in nodes_added:
            G.add_edge(s_str, o_str, label=p_name)

    if len(G.nodes()) == 0:
        print("No nodes to visualize with current filters")
        return

    # Create visualization
    plt.figure(figsize=figsize)
    plt.title(f"Leuphana Knowledge Graph ({len(G.nodes())} nodes, {len(G.edges())} edges)", fontsize=14)

    # Layout - use spring layout (kamada_kawai requires scipy)
    pos = nx.spring_layout(G, k=2, iterations=100, seed=42)

    # Draw nodes
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8)

    # Draw edges
    nx.draw_networkx_edges(G, pos, edge_color='gray', alpha=0.5, arrows=True, arrowsize=10)

    # Draw labels
    nx.draw_networkx_labels(G, pos, node_labels, font_size=7)

    # Create legend
    legend_elements = []
    for type_name, color in colors.items():
        if any(G.nodes[n].get('type') == type_name for n in G.nodes()):
            from matplotlib.patches import Patch
            legend_elements.append(Patch(facecolor=color, label=type_name))

    if legend_elements:
        plt.legend(handles=legend_elements, loc='upper left', fontsize=8)

    plt.axis('off')
    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved visualization to {output_file}")

    if show:
        plt.show()
    else:
        plt.close()

    return G


def visualize_hierarchy(rdf_file: str, output_file: str = None, show: bool = True):
    """
    Visualize just the organizational hierarchy (University > Schools > Institutes).
    """
    return visualize_kg_matplotlib(
        rdf_file,
        output_file=output_file,
        filter_types=["University", "School", "Institute"],
        max_nodes=50,
        figsize=(14, 10),
        show=show
    )


def visualize_school_members(rdf_file: str, school_name: str = None, output_file: str = None, show: bool = True):
    """
    Visualize members of a specific school or all schools with their staff.
    """
    return visualize_kg_matplotlib(
        rdf_file,
        output_file=output_file,
        filter_types=["School", "Institute", "Professor", "AcademicStaff", "Person"],
        max_nodes=150,
        figsize=(18, 14),
        show=show
    )


# =============================================================================
# Statistics and Summary
# =============================================================================

def generate_kg_summary(rdf_file: str) -> Dict[str, Any]:
    """
    Generate summary statistics for the knowledge graph.
    
    Args:
        rdf_file: Path to RDF file
    
    Returns:
        Dictionary with statistics
    """
    if not RDFLIB_AVAILABLE:
        print("Error: rdflib required")
        return {}
    
    g = Graph()
    g.parse(rdf_file, format="turtle")
    
    LEUPH = Namespace("http://leuphana.de/ontology#")
    
    # Count by type
    type_counts = {}
    for s, p, o in g.triples((None, RDF.type, None)):
        type_name = str(o).split('#')[-1].split('/')[-1]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    # Count relationships
    rel_counts = {}
    for s, p, o in g:
        if str(p) != str(RDF.type):
            rel_name = str(p).split('#')[-1].split('/')[-1]
            rel_counts[rel_name] = rel_counts.get(rel_name, 0) + 1
    
    summary = {
        "total_triples": len(g),
        "unique_subjects": len(set(g.subjects())),
        "unique_predicates": len(set(g.predicates())),
        "unique_objects": len(set(g.objects())),
        "entity_counts": type_counts,
        "relationship_counts": rel_counts
    }
    
    return summary


# =============================================================================
# CLI
# =============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="KG Visualization Tools")
    subparsers = parser.add_subparsers(dest="command")

    # D3 export
    d3_parser = subparsers.add_parser("d3", help="Export to D3.js JSON")
    d3_parser.add_argument("input", help="Input RDF file")
    d3_parser.add_argument("output", help="Output JSON file")

    # DOT export
    dot_parser = subparsers.add_parser("dot", help="Export to Graphviz DOT")
    dot_parser.add_argument("input", help="Input RDF file")
    dot_parser.add_argument("output", help="Output DOT file")
    dot_parser.add_argument("--max-nodes", type=int, default=100, help="Max nodes")

    # HTML visualization
    html_parser = subparsers.add_parser("html", help="Generate HTML visualization")
    html_parser.add_argument("json_file", help="D3 JSON data file")
    html_parser.add_argument("output", help="Output HTML file")

    # Matplotlib visualization (Python native)
    plot_parser = subparsers.add_parser("plot", help="Visualize using matplotlib (Python)")
    plot_parser.add_argument("input", help="Input RDF file")
    plot_parser.add_argument("-o", "--output", help="Output image file (PNG, PDF, SVG)")
    plot_parser.add_argument("--max-nodes", type=int, default=100, help="Max nodes to display")
    plot_parser.add_argument("--no-show", action="store_true", help="Don't display plot, just save")

    # Hierarchy visualization
    hier_parser = subparsers.add_parser("hierarchy", help="Visualize organizational hierarchy only")
    hier_parser.add_argument("input", help="Input RDF file")
    hier_parser.add_argument("-o", "--output", help="Output image file")
    hier_parser.add_argument("--no-show", action="store_true", help="Don't display plot")

    # Summary
    summary_parser = subparsers.add_parser("summary", help="Generate summary statistics")
    summary_parser.add_argument("input", help="Input RDF file")

    args = parser.parse_args()

    if args.command == "d3":
        rdf_to_d3_json(args.input, args.output)
    elif args.command == "dot":
        rdf_to_dot(args.input, args.output, args.max_nodes)
    elif args.command == "html":
        generate_html_visualization(args.json_file, args.output)
    elif args.command == "plot":
        visualize_kg_matplotlib(
            args.input,
            output_file=args.output,
            max_nodes=args.max_nodes,
            show=not args.no_show
        )
    elif args.command == "hierarchy":
        visualize_hierarchy(
            args.input,
            output_file=args.output,
            show=not args.no_show
        )
    elif args.command == "summary":
        summary = generate_kg_summary(args.input)
        print(json.dumps(summary, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()