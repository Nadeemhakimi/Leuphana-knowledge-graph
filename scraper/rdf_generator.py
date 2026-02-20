#!/usr/bin/env python3
"""
Leuphana University Knowledge Graph - RDF Generator

This module converts the extracted JSON data into RDF triples
using the Leuphana ontology.

Author: Bachelor's Thesis Project
Supervisor: Debayan Banerjee
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD, FOAF, SKOS, DC

import sys
from pathlib import Path
# Add parent directory to path for imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from config import ONTOLOGY_NS, INSTANCE_NS, OUTPUT_CONFIG


# ============================================================================
# Namespace Definitions
# ============================================================================

# Define namespaces
LEUPH = Namespace(ONTOLOGY_NS)  # Ontology namespace
LEUPH_RES = Namespace(INSTANCE_NS)  # Instance/resource namespace
SCHEMA = Namespace("http://schema.org/")
VIVO = Namespace("http://vivoweb.org/ontology/core#")


# ============================================================================
# RDF Generator Class
# ============================================================================

class RDFGenerator:
    """
    Generates RDF triples from extracted JSON data.
    
    Uses the Leuphana ontology to create a semantic representation
    of the university's academic structure.
    """
    
    def __init__(self):
        self.graph = Graph()
        self._bind_namespaces()
    
    def _bind_namespaces(self):
        """Bind namespace prefixes for cleaner Turtle output."""
        self.graph.bind("leuph", LEUPH)
        self.graph.bind("res", LEUPH_RES)
        self.graph.bind("foaf", FOAF)
        self.graph.bind("schema", SCHEMA)
        self.graph.bind("skos", SKOS)
        self.graph.bind("dc", DC)
        self.graph.bind("vivo", VIVO)
    
    def uri_from_string(self, uri_string: str) -> URIRef:
        """Convert a URI string to a URIRef."""
        return URIRef(uri_string)

    def name_to_uri(self, entity_type: str, name: str) -> URIRef:
        """Convert an entity name to a URI.

        This creates URIs in the format: http://leuphana.de/resource/{type}/{slug}
        """
        import re
        # Create URL-safe slug from name
        slug = name.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)  # Remove special chars
        slug = re.sub(r'\s+', '-', slug)  # Replace spaces with hyphens
        slug = re.sub(r'-+', '-', slug)  # Remove multiple hyphens
        slug = slug.strip('-')

        return URIRef(f"{INSTANCE_NS}{entity_type}/{slug}")
    
    def add_organization(self, org_data: Dict[str, Any]):
        """Add an organization to the graph."""
        uri = self.uri_from_string(org_data["uri"])
        org_type = org_data.get("org_type", "Organization")
        
        # Determine the class based on org_type
        type_mapping = {
            "University": LEUPH.University,
            "School": LEUPH.School,
            "Institute": LEUPH.Institute,
            "ResearchCenter": LEUPH.ResearchCenter,
            "ResearchGroup": LEUPH.ResearchGroup,
            "Chair": LEUPH.Chair,
            "College": LEUPH.College,
            "GraduateSchool": LEUPH.GraduateSchool,
            "ProfessionalSchool": LEUPH.ProfessionalSchool,
        }
        
        rdf_type = type_mapping.get(org_type, FOAF.Organization)
        
        # Add triples
        self.graph.add((uri, RDF.type, rdf_type))
        self.graph.add((uri, LEUPH.name, Literal(org_data["name"], lang="en")))
        self.graph.add((uri, RDFS.label, Literal(org_data["name"], lang="en")))
        
        if org_data.get("abbreviation"):
            self.graph.add((uri, LEUPH.abbreviation, Literal(org_data["abbreviation"])))
        
        if org_data.get("description"):
            self.graph.add((uri, LEUPH.description, Literal(org_data["description"], lang="en")))
            self.graph.add((uri, DC.description, Literal(org_data["description"], lang="en")))
        
        if org_data.get("parent"):
            parent_uri = self.uri_from_string(org_data["parent"])
            self.graph.add((uri, LEUPH.partOf, parent_uri))
            self.graph.add((parent_uri, LEUPH.hasPart, uri))
            
            # More specific relationship for institutes
            if org_type == "Institute":
                self.graph.add((uri, LEUPH.belongsTo, parent_uri))
        
        if org_data.get("webpage"):
            self.graph.add((uri, LEUPH.webpage, URIRef(org_data["webpage"])))
            self.graph.add((uri, FOAF.homepage, URIRef(org_data["webpage"])))
        
        if org_data.get("address"):
            self.graph.add((uri, LEUPH.address, Literal(org_data["address"])))
    
    def add_person(self, person_data: Dict[str, Any]):
        """Add a person to the graph."""
        uri = self.uri_from_string(person_data["uri"])
        category = person_data.get("category", "AcademicStaff")
        
        # Determine the class based on category
        category_mapping = {
            "Professor": LEUPH.Professor,
            "JuniorProfessor": LEUPH.JuniorProfessor,
            "HonoraryProfessor": LEUPH.HonoraryProfessor,
            "EmeritusProfessor": LEUPH.EmeritusProfessor,
            "VisitingProfessor": LEUPH.VisitingProfessor,
            "AdjunctProfessor": LEUPH.AdjunctProfessor,
            "ResearchAssistant": LEUPH.ResearchAssistant,
            "PostDoc": LEUPH.PostDoc,
            "PhDStudent": LEUPH.PhDStudent,
            "Lecturer": LEUPH.Lecturer,
            "VisitingScientist": LEUPH.VisitingScientist,
            "StudentAssistant": LEUPH.StudentAssistant,
            "AdministrativeStaff": LEUPH.AdministrativeStaff,
            "AcademicStaff": LEUPH.AcademicStaff,
        }
        
        rdf_type = category_mapping.get(category, LEUPH.AcademicStaff)
        
        # Add triples
        self.graph.add((uri, RDF.type, rdf_type))
        self.graph.add((uri, RDF.type, FOAF.Person))
        self.graph.add((uri, LEUPH.name, Literal(person_data["name"])))
        self.graph.add((uri, RDFS.label, Literal(person_data["name"])))
        self.graph.add((uri, FOAF.name, Literal(person_data["name"])))
        
        if person_data.get("first_name"):
            self.graph.add((uri, LEUPH.firstName, Literal(person_data["first_name"])))
            self.graph.add((uri, FOAF.firstName, Literal(person_data["first_name"])))
        
        if person_data.get("last_name"):
            self.graph.add((uri, LEUPH.lastName, Literal(person_data["last_name"])))
            self.graph.add((uri, FOAF.lastName, Literal(person_data["last_name"])))
        
        if person_data.get("title"):
            self.graph.add((uri, LEUPH.title, Literal(person_data["title"])))
        
        if person_data.get("email"):
            email = person_data["email"]
            self.graph.add((uri, LEUPH.email, Literal(email)))
            self.graph.add((uri, FOAF.mbox, URIRef(f"mailto:{email}")))
        
        if person_data.get("phone"):
            self.graph.add((uri, LEUPH.phone, Literal(person_data["phone"])))
        
        if person_data.get("office"):
            self.graph.add((uri, LEUPH.office, Literal(person_data["office"])))
        
        if person_data.get("webpage"):
            self.graph.add((uri, LEUPH.webpage, URIRef(person_data["webpage"])))
            self.graph.add((uri, FOAF.homepage, URIRef(person_data["webpage"])))
        
        # Try to link person to an organization
        org_linked = False

        if person_data.get("institute"):
            # Find matching institute by abbreviation or name
            institute_abbrev = person_data["institute"].upper()
            institute_uri = None

            # Search for existing institute with matching abbreviation
            for s in self.graph.subjects(RDF.type, LEUPH.Institute):
                # Check abbreviation
                for abbrev in self.graph.objects(s, LEUPH.abbreviation):
                    if str(abbrev).upper() == institute_abbrev:
                        institute_uri = s
                        break
                # Also check if abbreviation is in the URI
                if not institute_uri and institute_abbrev.lower() in str(s).lower():
                    institute_uri = s
                if institute_uri:
                    break

            # Also check ResearchCenters
            if not institute_uri:
                for s in self.graph.subjects(RDF.type, LEUPH.ResearchCenter):
                    if institute_abbrev.lower() in str(s).lower():
                        institute_uri = s
                        break

            # Also check Chairs
            if not institute_uri:
                for s in self.graph.subjects(RDF.type, LEUPH.Chair):
                    if institute_abbrev.lower() in str(s).lower():
                        institute_uri = s
                        break

            if institute_uri:
                self.graph.add((uri, LEUPH.memberOf, institute_uri))
                self.graph.add((institute_uri, LEUPH.hasMember, uri))
                org_linked = True

        if person_data.get("school"):
            # Create proper relationship to School node
            school_uri = self.name_to_uri("school", person_data["school"])
            self.graph.add((uri, LEUPH.worksAt, school_uri))
            # Add inverse relationship
            self.graph.add((school_uri, LEUPH.hasEmployee, uri))
            org_linked = True

        # Fallback: Link to University if no organization connection was made
        # This ensures no person is completely disconnected in the graph
        if not org_linked:
            university_uri = URIRef(f"{INSTANCE_NS}university/leuphana")
            self.graph.add((uri, LEUPH.affiliatedWith, university_uri))
            self.graph.add((university_uri, LEUPH.hasAffiliate, uri))

        # Research areas (kept as literals since we don't have ResearchArea entities yet)
        for area in person_data.get("research_areas", []):
            self.graph.add((uri, LEUPH.hasResearchArea, Literal(area)))
    
    def add_program(self, program_data: Dict[str, Any]):
        """Add a study program to the graph."""
        uri = self.uri_from_string(program_data["uri"])
        program_type = program_data.get("program_type", "StudyProgram")
        
        # Determine the class based on program_type
        type_mapping = {
            "BachelorProgram": LEUPH.BachelorProgram,
            "MasterProgram": LEUPH.MasterProgram,
            "DoctoralProgram": LEUPH.DoctoralProgram,
            "StudyProgram": LEUPH.StudyProgram,
        }
        
        rdf_type = type_mapping.get(program_type, LEUPH.StudyProgram)
        
        # Add triples
        self.graph.add((uri, RDF.type, rdf_type))
        self.graph.add((uri, LEUPH.name, Literal(program_data["name"], lang="en")))
        self.graph.add((uri, RDFS.label, Literal(program_data["name"], lang="en")))
        
        if program_data.get("description"):
            self.graph.add((uri, LEUPH.description, Literal(program_data["description"], lang="en")))
        
        if program_data.get("duration"):
            self.graph.add((uri, LEUPH.duration, Literal(program_data["duration"])))
        
        if program_data.get("language"):
            self.graph.add((uri, LEUPH.language, Literal(program_data["language"])))
        
        if program_data.get("offered_by"):
            # Resolve the URI to an existing organization
            offered_by_uri = self._resolve_org_uri(program_data["offered_by"])
            self.graph.add((uri, LEUPH.offeredBy, offered_by_uri))
            self.graph.add((offered_by_uri, LEUPH.offers, uri))
        else:
            # Fallback: Link to University
            university_uri = URIRef(f"{INSTANCE_NS}university/leuphana")
            self.graph.add((uri, LEUPH.offeredBy, university_uri))
            self.graph.add((university_uri, LEUPH.offers, uri))

        if program_data.get("webpage"):
            self.graph.add((uri, LEUPH.webpage, URIRef(program_data["webpage"])))
    
    def add_chair(self, chair_data: Dict[str, Any]):
        """Add a Chair (Professorship/Lehrstuhl) to the graph.
        
        This creates:
        - Chair entity as leuph:Chair
        - heads relationship from Professor to Chair
        - memberOf relationships for team members
        - partOf relationship to parent Institute
        """
        uri = self.uri_from_string(chair_data["uri"])
        
        # Add type
        self.graph.add((uri, RDF.type, LEUPH.Chair))
        self.graph.add((uri, RDF.type, FOAF.Organization))
        
        # Add name and label
        self.graph.add((uri, LEUPH.name, Literal(chair_data["name"], lang="en")))
        self.graph.add((uri, RDFS.label, Literal(chair_data["name"], lang="en")))
        
        # Add description
        if chair_data.get("description"):
            self.graph.add((uri, LEUPH.description, Literal(chair_data["description"], lang="en")))
        
        # Add partOf relationship to parent organization (Institute)
        parent_linked = False
        if chair_data.get("parent"):
            parent_uri = self.uri_from_string(chair_data["parent"])
            self.graph.add((uri, LEUPH.partOf, parent_uri))
            self.graph.add((parent_uri, LEUPH.hasPart, uri))
            parent_linked = True

        # Fallback: Link to University if no parent organization
        if not parent_linked:
            university_uri = URIRef(f"{INSTANCE_NS}university/leuphana")
            self.graph.add((uri, LEUPH.partOf, university_uri))
            self.graph.add((university_uri, LEUPH.hasPart, uri))

        # Add heads relationship - Professor heads Chair
        if chair_data.get("headed_by"):
            professor_uri = self.uri_from_string(chair_data["headed_by"])
            # The professor heads the chair
            self.graph.add((professor_uri, LEUPH.heads, uri))
            # Inverse: the chair is headed by the professor
            self.graph.add((uri, LEUPH.headedBy, professor_uri))
        
        # Add team members
        for member_uri_str in chair_data.get("team_members", []):
            member_uri = self.uri_from_string(member_uri_str)
            # Member is member of the chair
            self.graph.add((member_uri, LEUPH.memberOf, uri))
            # Chair has member
            self.graph.add((uri, LEUPH.hasMember, member_uri))
        
        # Add webpage
        if chair_data.get("webpage"):
            self.graph.add((uri, LEUPH.webpage, URIRef(chair_data["webpage"])))
            self.graph.add((uri, FOAF.homepage, URIRef(chair_data["webpage"])))
    
    def add_hiwi_position(self, hiwi_data: Dict[str, Any]):
        """Add a Hiwi (Student Assistant) position posting to the graph.
        
        This answers the competency question: "What Hiwi positions are currently available?"
        """
        uri = self.uri_from_string(hiwi_data["uri"])
        
        # Add type
        self.graph.add((uri, RDF.type, LEUPH.HiwiPosition))
        
        # Add title/name
        self.graph.add((uri, LEUPH.name, Literal(hiwi_data["title"], lang="en")))
        self.graph.add((uri, RDFS.label, Literal(hiwi_data["title"], lang="en")))
        
        # Add description
        if hiwi_data.get("description"):
            self.graph.add((uri, LEUPH.description, Literal(hiwi_data["description"], lang="en")))
        
        # Add department/institute relationship
        if hiwi_data.get("department"):
            dept_uri = self.name_to_uri("institute", hiwi_data["department"])
            self.graph.add((uri, LEUPH.postedBy, dept_uri))
        
        # Add contact email
        if hiwi_data.get("contact_email"):
            self.graph.add((uri, LEUPH.contactEmail, Literal(hiwi_data["contact_email"])))
        
        # Add posted date
        if hiwi_data.get("posted_date"):
            self.graph.add((uri, LEUPH.postedDate, Literal(hiwi_data["posted_date"], datatype=XSD.date)))
        
        # Add hours per week
        if hiwi_data.get("hours_per_week"):
            self.graph.add((uri, LEUPH.hoursPerWeek, Literal(hiwi_data["hours_per_week"])))
        
        # Add webpage
        if hiwi_data.get("webpage"):
            self.graph.add((uri, LEUPH.webpage, URIRef(hiwi_data["webpage"])))

    def add_minor(self, minor_data: Dict[str, Any]):
        """Add a Minor program to the graph.

        Minors are secondary study fields in the Bachelor program.
        """
        uri = self.uri_from_string(minor_data["uri"])

        # Add type
        self.graph.add((uri, RDF.type, LEUPH.Minor))

        # Add name (English and German)
        self.graph.add((uri, LEUPH.name, Literal(minor_data["name"], lang="en")))
        self.graph.add((uri, RDFS.label, Literal(minor_data["name"], lang="en")))

        if minor_data.get("name_de"):
            self.graph.add((uri, LEUPH.name, Literal(minor_data["name_de"], lang="de")))
            self.graph.add((uri, RDFS.label, Literal(minor_data["name_de"], lang="de")))

        # Add description
        if minor_data.get("description"):
            self.graph.add((uri, LEUPH.description, Literal(minor_data["description"], lang="de")))

        # Add credit points
        if minor_data.get("credit_points"):
            self.graph.add((uri, LEUPH.credits, Literal(minor_data["credit_points"], datatype=XSD.integer)))

        # Add offered_by relationship
        if minor_data.get("offered_by"):
            offered_by_uri = self.uri_from_string(minor_data["offered_by"])
            self.graph.add((uri, LEUPH.offeredBy, offered_by_uri))
            self.graph.add((offered_by_uri, LEUPH.offers, uri))

        # Add webpage
        if minor_data.get("webpage"):
            self.graph.add((uri, LEUPH.webpage, URIRef(minor_data["webpage"])))

    def add_research_project(self, project_data: Dict[str, Any]):
        """Add a Research Project to the graph.

        This captures research activities conducted by institutes and centers.
        """
        uri = self.uri_from_string(project_data["uri"])

        # Add type
        self.graph.add((uri, RDF.type, LEUPH.ResearchProject))

        # Add name
        self.graph.add((uri, LEUPH.name, Literal(project_data["name"], lang="en")))
        self.graph.add((uri, RDFS.label, Literal(project_data["name"], lang="en")))

        # Add description
        if project_data.get("description"):
            self.graph.add((uri, LEUPH.description, Literal(project_data["description"])))

        # Add conducted_by relationship (to organization)
        if project_data.get("conducted_by"):
            # Resolve the URI to an existing organization
            org_uri = self._resolve_org_uri(project_data["conducted_by"])
            self.graph.add((uri, LEUPH.conductedBy, org_uri))
            self.graph.add((org_uri, LEUPH.conducts, uri))
        else:
            # Fallback: Link to University
            university_uri = URIRef(f"{INSTANCE_NS}university/leuphana")
            self.graph.add((uri, LEUPH.conductedBy, university_uri))
            self.graph.add((university_uri, LEUPH.conducts, uri))

        # Add principal investigator relationship
        if project_data.get("principal_investigator"):
            pi_uri = self.uri_from_string(project_data["principal_investigator"])
            self.graph.add((pi_uri, LEUPH.worksOn, uri))

        # Add funding source
        if project_data.get("funding_source"):
            self.graph.add((uri, LEUPH.fundingSource, Literal(project_data["funding_source"])))

        # Add start/end dates
        if project_data.get("start_date"):
            self.graph.add((uri, LEUPH.startDate, Literal(project_data["start_date"], datatype=XSD.date)))

        if project_data.get("end_date"):
            self.graph.add((uri, LEUPH.endDate, Literal(project_data["end_date"], datatype=XSD.date)))

        # Add webpage
        if project_data.get("webpage"):
            self.graph.add((uri, LEUPH.webpage, URIRef(project_data["webpage"])))

    def add_course(self, course_data: Dict[str, Any]):
        """Add a Course to the graph.

        This creates the critical relationships:
        - Course entity as leuph:Course
        - teaches relationship: Professor -> teaches -> Course
        - partOf relationship: Course -> partOf -> Program

        These relationships enable answering: "Who teaches in the Major?"
        """
        uri = self.uri_from_string(course_data["uri"])

        # Add type - Course is a subclass of schema:Course
        self.graph.add((uri, RDF.type, LEUPH.Course))
        self.graph.add((uri, RDF.type, SCHEMA.Course))

        # Add name and label
        self.graph.add((uri, LEUPH.name, Literal(course_data["name"], lang="en")))
        self.graph.add((uri, RDFS.label, Literal(course_data["name"], lang="en")))

        # Add description
        if course_data.get("description"):
            self.graph.add((uri, LEUPH.description, Literal(course_data["description"], lang="en")))

        # Add credit points
        if course_data.get("credit_points"):
            self.graph.add((uri, LEUPH.credits, Literal(course_data["credit_points"], datatype=XSD.integer)))

        # Add course type (Lecture, Seminar, Tutorial, etc.)
        if course_data.get("course_type"):
            self.graph.add((uri, LEUPH.courseType, Literal(course_data["course_type"])))

        # Add semester
        if course_data.get("semester"):
            self.graph.add((uri, LEUPH.semester, Literal(course_data["semester"])))

        # Add language
        if course_data.get("language"):
            self.graph.add((uri, LEUPH.language, Literal(course_data["language"])))

        # Add partOf relationship to program
        # This creates: Course -> partOf -> Program
        program_linked = False
        if course_data.get("part_of_program"):
            program_uri = self.uri_from_string(course_data["part_of_program"])
            self.graph.add((uri, LEUPH.partOf, program_uri))
            self.graph.add((program_uri, LEUPH.hasPart, uri))
            program_linked = True

        # Fallback: Link to College/University if no program connection
        # This ensures courses aren't completely disconnected
        if not program_linked:
            # Link to College as default academic unit for courses
            college_uri = URIRef(f"{INSTANCE_NS}school/college")
            self.graph.add((uri, LEUPH.offeredBy, college_uri))
            self.graph.add((college_uri, LEUPH.offers, uri))

        # Add teaches relationship - the critical connection
        # This creates: Professor -> teaches -> Course
        for instructor_uri_str in course_data.get("taught_by", []):
            instructor_uri = self.uri_from_string(instructor_uri_str)
            self.graph.add((instructor_uri, LEUPH.teaches, uri))
            self.graph.add((uri, LEUPH.taughtBy, instructor_uri))

        # Add webpage
        if course_data.get("webpage"):
            self.graph.add((uri, LEUPH.webpage, URIRef(course_data["webpage"])))

    def _create_core_academic_units(self):
        """Create College, Graduate School, and Professional School if they don't exist.

        These are the main academic units that programs are offered by.
        """
        university_uri = URIRef(f"{INSTANCE_NS}university/leuphana")

        # Define the core academic units
        core_units = [
            {
                "uri": f"{INSTANCE_NS}school/college",
                "name": "College",
                "description": "Leuphana College offers undergraduate (Bachelor) programs"
            },
            {
                "uri": f"{INSTANCE_NS}school/graduate-school",
                "name": "Graduate School",
                "description": "Leuphana Graduate School offers Master's programs"
            },
            {
                "uri": f"{INSTANCE_NS}school/professional-school",
                "name": "Professional School",
                "description": "Leuphana Professional School offers professional and continuing education programs"
            }
        ]

        for unit in core_units:
            uri = URIRef(unit["uri"])
            # Check if already exists
            if (uri, RDF.type, LEUPH.School) not in self.graph:
                self.graph.add((uri, RDF.type, LEUPH.School))
                self.graph.add((uri, LEUPH.name, Literal(unit["name"], lang="en")))
                self.graph.add((uri, RDFS.label, Literal(unit["name"], lang="en")))
                self.graph.add((uri, LEUPH.description, Literal(unit["description"], lang="en")))
                # Link to University
                self.graph.add((uri, LEUPH.partOf, university_uri))
                self.graph.add((university_uri, LEUPH.hasPart, uri))

    def _resolve_org_uri(self, uri_string: str) -> URIRef:
        """Resolve an organization URI to an existing organization in the graph.

        Handles abbreviated URIs like 'institute/imo' by matching to full URIs
        like 'institute/institute-of-management-and-organization-imo'.
        """
        uri = URIRef(uri_string)

        # If URI already exists in graph, use it directly
        if (uri, RDF.type, None) in self.graph:
            return uri

        # Extract the abbreviated part from the URI
        # e.g., 'http://leuphana.de/resource/institute/imo' -> 'imo'
        parts = uri_string.rstrip('/').split('/')
        abbrev = parts[-1].lower() if parts else ''
        entity_type = parts[-2] if len(parts) >= 2 else ''

        # Try to find matching organization by abbreviation in URI
        type_to_class = {
            'institute': LEUPH.Institute,
            'research-center': LEUPH.ResearchCenter,
            'school': LEUPH.School,
        }

        rdf_class = type_to_class.get(entity_type)
        if rdf_class:
            for s in self.graph.subjects(RDF.type, rdf_class):
                s_str = str(s).lower()
                # Check if abbreviation appears in the full URI
                if abbrev in s_str or s_str.endswith(abbrev):
                    return s
                # Also check the abbreviation property
                for abbr_lit in self.graph.objects(s, LEUPH.abbreviation):
                    if str(abbr_lit).lower() == abbrev:
                        return s

        # Fallback: return University if no match found
        return URIRef(f"{INSTANCE_NS}university/leuphana")

    def load_from_json(self, json_file: str):
        """Load data from combined JSON file."""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Process organizations
        print(f"Processing {len(data.get('organizations', {}))} organizations...")
        for uri, org_data in data.get("organizations", {}).items():
            self.add_organization(org_data)

        # Create core academic units (College, Graduate School, Professional School)
        self._create_core_academic_units()

        # Process chairs (after organizations, before persons)
        print(f"Processing {len(data.get('chairs', {}))} chairs...")
        for uri, chair_data in data.get("chairs", {}).items():
            self.add_chair(chair_data)
        
        # Process Hiwi positions
        print(f"Processing {len(data.get('hiwi_positions', {}))} Hiwi positions...")
        for uri, hiwi_data in data.get("hiwi_positions", {}).items():
            self.add_hiwi_position(hiwi_data)
        
        # Process persons
        print(f"Processing {len(data.get('persons', {}))} persons...")
        for uri, person_data in data.get("persons", {}).items():
            self.add_person(person_data)
        
        # Process programs
        print(f"Processing {len(data.get('programs', {}))} programs...")
        for uri, program_data in data.get("programs", {}).items():
            self.add_program(program_data)

        # Process minors
        print(f"Processing {len(data.get('minors', {}))} minors...")
        for uri, minor_data in data.get("minors", {}).items():
            self.add_minor(minor_data)

        # Process research projects
        print(f"Processing {len(data.get('research_projects', {}))} research projects...")
        for uri, project_data in data.get("research_projects", {}).items():
            self.add_research_project(project_data)

        # Process courses (after programs and persons for relationship linking)
        print(f"Processing {len(data.get('courses', {}))} courses...")
        for uri, course_data in data.get("courses", {}).items():
            self.add_course(course_data)

    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about the generated graph."""
        stats = {
            "total_triples": len(self.graph),
            "universities": len(list(self.graph.subjects(RDF.type, LEUPH.University))),
            "schools": len(list(self.graph.subjects(RDF.type, LEUPH.School))),
            "institutes": len(list(self.graph.subjects(RDF.type, LEUPH.Institute))),
            "research_centers": len(list(self.graph.subjects(RDF.type, LEUPH.ResearchCenter))),
            "chairs": len(list(self.graph.subjects(RDF.type, LEUPH.Chair))),
            "hiwi_positions": len(list(self.graph.subjects(RDF.type, LEUPH.HiwiPosition))),
            "professors": len(list(self.graph.subjects(RDF.type, LEUPH.Professor))),
            "persons": len(list(self.graph.subjects(RDF.type, FOAF.Person))),
            "programs": len(list(self.graph.subjects(RDF.type, LEUPH.StudyProgram))),
            "minors": len(list(self.graph.subjects(RDF.type, LEUPH.Minor))),
            "courses": len(list(self.graph.subjects(RDF.type, LEUPH.Course))),
            "research_projects": len(list(self.graph.subjects(RDF.type, LEUPH.ResearchProject))),
            "heads_relationships": len(list(self.graph.subject_objects(LEUPH.heads))),
            "teaches_relationships": len(list(self.graph.subject_objects(LEUPH.teaches))),
        }
        return stats
    
    def serialize(self, output_file: str, format: str = "turtle"):
        """Serialize the graph to a file."""
        self.graph.serialize(destination=output_file, format=format)
        print(f"Graph serialized to {output_file} ({format} format)")
    
    def serialize_ntriples(self, output_file: str):
        """Serialize to N-Triples format (good for bulk import)."""
        self.graph.serialize(destination=output_file, format="nt")
        print(f"Graph serialized to {output_file} (N-Triples format)")
    
    def serialize_jsonld(self, output_file: str):
        """Serialize to JSON-LD format."""
        self.graph.serialize(destination=output_file, format="json-ld")
        print(f"Graph serialized to {output_file} (JSON-LD format)")


# ============================================================================
# Main Function
# ============================================================================

def main():
    """Main function to generate RDF from scraped data."""
    print("=" * 60)
    print("Leuphana University Knowledge Graph - RDF Generator")
    print("=" * 60)
    
    # Input and output paths
    input_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / "latest.json"
    rdf_dir = Path(OUTPUT_CONFIG["rdf_dir"])
    rdf_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Check if input exists
    if not input_file.exists():
        print(f"Error: Input file {input_file} not found.")
        print("Please run the scraper first: python scraper.py")
        return
    
    # Generate RDF
    generator = RDFGenerator()
    generator.load_from_json(str(input_file))
    
    # Print statistics
    stats = generator.get_statistics()
    print("\n=== Graph Statistics ===")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Serialize to different formats
    print("\n=== Serializing Graph ===")
    
    # Turtle (human-readable)
    turtle_file = rdf_dir / f"leuphana_kg_{timestamp}.ttl"
    generator.serialize(str(turtle_file), format="turtle")
    
    # Also save as 'latest'
    generator.serialize(str(rdf_dir / "leuphana_kg_latest.ttl"), format="turtle")
    
    # N-Triples (for bulk import)
    nt_file = rdf_dir / f"leuphana_kg_{timestamp}.nt"
    generator.serialize_ntriples(str(nt_file))
    generator.serialize_ntriples(str(rdf_dir / "leuphana_kg_latest.nt"))
    
    # JSON-LD (for web applications)
    jsonld_file = rdf_dir / f"leuphana_kg_{timestamp}.jsonld"
    generator.serialize_jsonld(str(jsonld_file))
    generator.serialize_jsonld(str(rdf_dir / "leuphana_kg_latest.jsonld"))
    
    print("\n" + "=" * 60)
    print("RDF generation complete!")
    print(f"Files saved to: {rdf_dir}")
    print("=" * 60)


if __name__ == "__main__":
    main()