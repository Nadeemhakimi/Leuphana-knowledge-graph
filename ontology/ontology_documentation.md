# Leuphana University Ontology Documentation

## Overview

This ontology represents the organizational and academic structure of Leuphana University of Lüneburg. It captures entities such as schools (faculties), institutes, professors, staff, study programs, and their relationships.

## Namespace

- **Ontology URI**: `http://leuphana.de/ontology#`
- **Preferred Prefix**: `leuph`
- **Instance Namespace**: `http://leuphana.de/resource/`

## External Vocabularies Used

The ontology reuses and extends the following established vocabularies:

| Prefix   | Namespace                            | Usage                              |
| -------- | ------------------------------------ | ---------------------------------- |
| `foaf`   | http://xmlns.com/foaf/0.1/           | Person and Organization classes    |
| `schema` | http://schema.org/                   | Course and EducationalOrganization |
| `dc`     | http://purl.org/dc/elements/1.1/     | Metadata (title, description)      |
| `skos`   | http://www.w3.org/2004/02/skos/core# | Labels and definitions             |

## Classes

### Organizational Structure

| Class                  | Parent              | Description                  |
| ---------------------- | ------------------- | ---------------------------- |
| `leuph:University`     | `foaf:Organization` | The university itself        |
| `leuph:School`         | `foaf:Organization` | A research school/faculty    |
| `leuph:Institute`      | `foaf:Organization` | An institute within a school |
| `leuph:ResearchCenter` | `foaf:Organization` | A research center            |
| `leuph:ResearchGroup`  | `foaf:Organization` | A research group             |
| `leuph:Chair`          | `foaf:Organization` | A professorial chair         |

### Teaching Schools

| Class                      | Parent                 | Description                         |
| -------------------------- | ---------------------- | ----------------------------------- |
| `leuph:TeachingSchool`     | `foaf:Organization`    | Abstract class for teaching schools |
| `leuph:College`            | `leuph:TeachingSchool` | Bachelor's programs                 |
| `leuph:GraduateSchool`     | `leuph:TeachingSchool` | Master's and doctoral programs      |
| `leuph:ProfessionalSchool` | `leuph:TeachingSchool` | Continuing education                |

### Persons

| Class                       | Parent                | Description                     |
| --------------------------- | --------------------- | ------------------------------- |
| `leuph:AcademicStaff`       | `foaf:Person`         | Academic staff (abstract)       |
| `leuph:Professor`           | `leuph:AcademicStaff` | Full professor                  |
| `leuph:JuniorProfessor`     | `leuph:Professor`     | Junior professor (tenure track) |
| `leuph:HonoraryProfessor`   | `leuph:Professor`     | Honorary professor              |
| `leuph:EmeritusProfessor`   | `leuph:Professor`     | Emeritus professor              |
| `leuph:VisitingProfessor`   | `leuph:Professor`     | Visiting professor              |
| `leuph:AdjunctProfessor`    | `leuph:Professor`     | Adjunct professor               |
| `leuph:ResearchAssistant`   | `leuph:AcademicStaff` | Research assistant              |
| `leuph:PostDoc`             | `leuph:AcademicStaff` | Post-doctoral researcher        |
| `leuph:PhDStudent`          | `leuph:AcademicStaff` | Doctoral student                |
| `leuph:Lecturer`            | `leuph:AcademicStaff` | Lecturer                        |
| `leuph:VisitingScientist`   | `leuph:AcademicStaff` | Visiting scientist              |
| `leuph:AdministrativeStaff` | `foaf:Person`         | Administrative staff            |
| `leuph:StudentAssistant`    | `foaf:Person`         | Student assistant (HiWi)        |
| `leuph:Dean`                | `leuph:Professor`     | Dean of a school                |

### Academic Programs

| Class                   | Parent               | Description                              |
| ----------------------- | -------------------- | ---------------------------------------- |
| `leuph:StudyProgram`    | `schema:Course`      | Academic study program                   |
| `leuph:BachelorProgram` | `leuph:StudyProgram` | Bachelor program                         |
| `leuph:MasterProgram`   | `leuph:StudyProgram` | Master program                           |
| `leuph:DoctoralProgram` | `leuph:StudyProgram` | Doctoral program                         |
| `leuph:Major`           | -                    | Major field of study                     |
| `leuph:Minor`           | -                    | Minor field of study                     |
| `leuph:Course`          | `schema:Course`      | Individual course                        |
| `leuph:Module`          | `schema:Course`      | Course module (group of related courses) |

### Research

| Class                   | Description              |
| ----------------------- | ------------------------ |
| `leuph:ResearchArea`    | A research area or focus |
| `leuph:ResearchProject` | A research project       |
| `leuph:Publication`     | An academic publication  |

### Positions

| Class                | Parent              | Description                |
| -------------------- | ------------------- | -------------------------- |
| `leuph:JobPosition`  | -                   | A job position             |
| `leuph:HiWiPosition` | `leuph:JobPosition` | Student assistant position |

## Object Properties

### Organizational Relationships

| Property          | Domain      | Range    | Description                  |
| ----------------- | ----------- | -------- | ---------------------------- |
| `leuph:partOf`    | `*`         | `*`      | Generic part-of relationship |
| `leuph:hasPart`   | `*`         | `*`      | Inverse of partOf            |
| `leuph:belongsTo` | `Institute` | `School` | Institute belongs to school  |

### Person-Organization Relationships

| Property            | Domain              | Range               | Description                      |
| ------------------- | ------------------- | ------------------- | -------------------------------- |
| `leuph:worksAt`     | `foaf:Person`       | `foaf:Organization` | Person works at organization     |
| `leuph:hasEmployee` | `foaf:Organization` | `foaf:Person`       | Inverse of worksAt               |
| `leuph:memberOf`    | `foaf:Person`       | `foaf:Organization` | Person is member of organization |
| `leuph:hasMember`   | `foaf:Organization` | `foaf:Person`       | Inverse of memberOf              |
| `leuph:heads`       | `foaf:Person`       | `foaf:Organization` | Person heads organization        |
| `leuph:headedBy`    | `foaf:Organization` | `foaf:Person`       | Inverse of heads                 |
| `leuph:deanOf`      | `Dean`              | `School`            | Dean of a school                 |

### Teaching Relationships

| Property             | Domain          | Range           | Description                  |
| -------------------- | --------------- | --------------- | ---------------------------- |
| `leuph:teaches`      | `AcademicStaff` | `Course`        | Staff teaches course         |
| `leuph:taughtBy`     | `Course`        | `AcademicStaff` | Inverse of teaches           |
| `leuph:teachesIn`    | `AcademicStaff` | `StudyProgram`  | Staff teaches in program     |
| `leuph:supervises`   | `Professor`     | `foaf:Person`   | Professor supervises student |
| `leuph:supervisedBy` | `foaf:Person`   | `Professor`     | Inverse of supervises        |

### Program Relationships

| Property          | Domain              | Range               | Description                     |
| ----------------- | ------------------- | ------------------- | ------------------------------- |
| `leuph:offeredBy` | `StudyProgram`      | `foaf:Organization` | Program offered by organization |
| `leuph:offers`    | `foaf:Organization` | `StudyProgram`      | Inverse of offeredBy            |

### Position Relationships

| Property            | Domain              | Range               | Description                     |
| ------------------- | ------------------- | ------------------- | ------------------------------- |
| `leuph:postedBy`    | `JobPosition`       | `foaf:Organization` | Position posted by organization |
| `leuph:hasPosition` | `foaf:Organization` | `JobPosition`       | Inverse of postedBy             |

### Research Relationships

| Property                | Domain                | Range             | Description          |
| ----------------------- | --------------------- | ----------------- | -------------------- |
| `leuph:hasResearchArea` | `Person/Organization` | `ResearchArea`    | Has research area    |
| `leuph:worksOn`         | `foaf:Person`         | `ResearchProject` | Works on project     |
| `leuph:authored`        | `foaf:Person`         | `Publication`     | Authored publication |

## Data Properties

### Identity Properties

| Property             | Domain              | Range        | Description                |
| -------------------- | ------------------- | ------------ | -------------------------- |
| `leuph:name`         | `*`                 | `xsd:string` | Name of entity             |
| `leuph:abbreviation` | `foaf:Organization` | `xsd:string` | Abbreviation (e.g., "IIS") |

### Person Properties

| Property          | Domain        | Range        | Description     |
| ----------------- | ------------- | ------------ | --------------- |
| `leuph:title`     | `foaf:Person` | `xsd:string` | Academic title  |
| `leuph:firstName` | `foaf:Person` | `xsd:string` | First name      |
| `leuph:lastName`  | `foaf:Person` | `xsd:string` | Last name       |
| `leuph:email`     | `foaf:Person` | `xsd:string` | Email address   |
| `leuph:phone`     | `foaf:Person` | `xsd:string` | Phone number    |
| `leuph:office`    | `foaf:Person` | `xsd:string` | Office location |

### General Properties

| Property            | Domain | Range        | Description      |
| ------------------- | ------ | ------------ | ---------------- |
| `leuph:webpage`     | `*`    | `xsd:anyURI` | Web page URL     |
| `leuph:description` | `*`    | `xsd:string` | Description text |
| `leuph:address`     | `*`    | `xsd:string` | Physical address |

### Academic Properties

| Property         | Domain         | Range         | Description             |
| ---------------- | -------------- | ------------- | ----------------------- |
| `leuph:credits`  | `Course`       | `xsd:integer` | ECTS credits            |
| `leuph:semester` | `Course`       | `xsd:string`  | Semester offered        |
| `leuph:duration` | `StudyProgram` | `xsd:string`  | Program duration        |
| `leuph:language` | `*`            | `xsd:string`  | Language of instruction |

### Position Properties

| Property             | Domain        | Range         | Description                |
| -------------------- | ------------- | ------------- | -------------------------- |
| `leuph:hoursPerWeek` | `JobPosition` | `xsd:integer` | Hours per week             |
| `leuph:postedDate`   | `JobPosition` | `xsd:date`    | Date position was posted   |
| `leuph:deadline`     | `JobPosition` | `xsd:date`    | Application deadline       |
| `leuph:contactEmail` | `JobPosition` | `xsd:string`  | Contact email for position |

## Design Decisions

### 1. Reuse of External Vocabularies

- FOAF for basic person/organization concepts
- Schema.org for educational entities
- This enables interoperability with other linked data sources

### 2. Professor Hierarchy

- Created a hierarchy of professor types reflecting German academic titles
- `JuniorProfessor`, `HonoraryProfessor`, etc. are subclasses of `Professor`

### 3. Organizational Hierarchy

- Used `partOf` relationship for generic containment
- Added specific `belongsTo` for Institute-School relationship
- Schools contain Institutes, which may contain Research Groups

### 4. Multilingual Support

- Labels support `@en` and `@de` language tags
- Primary data is in English for broader accessibility

### 5. Inverse Properties

- Defined inverse properties for key relationships
- Enables bidirectional navigation in the graph

## Competency Questions

The ontology is designed to answer:

1. Which professors work in which department?
2. Who teaches in which major?
3. Which chairs belong to which faculty?
4. Which research groups are associated with a professor?
5. What HiWi positions are currently available?
6. What is the contact information for a professor?
7. Which programs are offered by each school?
8. Who supervises doctoral students?

## Usage with Protégé

1. Open `leuphana.owl` in Protégé
2. Use the "Classes" tab to view the class hierarchy
3. Use the "Object Properties" tab to see relationships
4. Use the "Data Properties" tab to see attributes
5. Use the "Individuals" tab to view instances (after import)

## Usage with GraphDB

1. Import `leuphana.owl` as the base ontology
2. Import instance data from `data/rdf/leuphana_kg_latest.ttl`
3. Use SPARQL queries to explore relationships
4. Enable RDFS-Plus reasoning for inference

## Usage with Natural Language Queries

The ontology schema is automatically parsed by `visualization/nlq_chain.py` to provide context for LLM-based SPARQL generation. The system extracts:

- All class definitions and their hierarchy
- Object properties with domain/range constraints
- Data properties with their types

This enables users to ask questions in plain English (e.g., "Which professors work in which institute?") and receive valid SPARQL queries that respect the ontology structure.

## Validation

The ontology can be validated using:

- Protégé's built-in reasoner (e.g., Pellet, HermiT)
- SHACL constraints (see `shacl_shapes.ttl`)
- OWL API consistency checking
