"""
Configuration for Leuphana University Web Scraper
"""

# Base URLs
BASE_URL = "https://www.leuphana.de"
BASE_URL_EN = "https://www.leuphana.de/en"
BASE_URL_DE = "https://www.leuphana.de"

# Important starting URLs for scraping
SEED_URLS = {
    # Main institution pages
    "institutions": f"{BASE_URL_EN}/institutions.html",
    "faculty": f"{BASE_URL_EN}/institutions/faculty.html",
    
    # Schools (Faculties)
    "schools": {
        "education": f"{BASE_URL_EN}/institutions/faculty/education.html",
        "culture_society": f"{BASE_URL_EN}/institutions/faculty/humanities-social-sciences.html",
        "management_technology": f"{BASE_URL_EN}/institutions/faculty/management-and-technology.html",
        "sustainability": f"{BASE_URL_EN}/institutions/faculty/sustainability.html",
        "public_affairs": f"{BASE_URL_EN}/institutions/faculty/school-of-public-affairs.html",
    },
    
    # Staff directories (correct URLs per school)
    "staff": {
        # School of Education
        "education_institutes": f"{BASE_URL_EN}/institutions/faculty/education/institutes-of-the-faculty.html",
        # School of Culture and Society
        "culture_institutes": f"{BASE_URL_EN}/institutions/faculty/humanities-social-sciences/institutes.html",
        "culture_deans": f"{BASE_URL_EN}/institutions/faculty/humanities-social-sciences/about-the-school/deans-office.html",
        # School of Management and Technology
        "management_people": f"{BASE_URL_EN}/institutions/faculty/management-and-technology/about-the-school/people-directory.html",
        "management_institutes": f"{BASE_URL_EN}/institutions/faculty/management-and-technology/institutes-professors.html",
        # School of Sustainability
        "sustainability_institutes": f"{BASE_URL_EN}/institutions/faculty/sustainability/institutes-1.html",
        "sustainability_deans": f"{BASE_URL_EN}/institutions/faculty/sustainability/about-the-school/deans-office.html",
        # School of Public Affairs
        "public_affairs_institutes": f"{BASE_URL_EN}/institutions/faculty/school-of-public-affairs/institutes-and-professors.html",
        "public_affairs_deans": f"{BASE_URL_EN}/institutions/faculty/school-of-public-affairs/about-school-of-public-affairs/deans-office.html",
    },
    
    # Teaching schools
    "teaching": {
        "college": f"{BASE_URL_EN}/college.html",
        "graduate_school": f"{BASE_URL_EN}/graduate-school.html",
        "professional_school": f"{BASE_URL_EN}/professional-school.html",
    },

    # Study programs
    "programs": {
        "bachelor": f"{BASE_URL_EN}/college/bachelor.html",  # Fixed URL
        "master": f"{BASE_URL_EN}/graduate-school/masters-programmes.html",
        "professional": f"{BASE_URL_EN}/professional-school/masters-studies.html",
    },

    # Research
    "research": f"{BASE_URL_EN}/research.html",
    "research_centers": f"{BASE_URL_EN}/institutions/faculty/research-centers.html",

    # HiWi/Student Assistant job postings
    "hiwi_positions": f"{BASE_URL}/universitaet/jobs-und-karriere/hilfskraefte.html",

    # Course catalog (Vorlesungsverzeichnis)
    "vorlesungsverzeichnis": f"{BASE_URL}/services/vorlesungsverzeichnis.html",
}

# URL patterns to identify entity types
URL_PATTERNS = {
    "school": r"/institutions/faculty/[^/]+\.html$",
    "institute": r"/institutes/[^/]+\.html$",
    "professor": r"/universitaet/person/[^/]+\.html$",
    "person_profile": r"/en/university/person/[^/]+\.html$",
    "program": r"/(college|graduate-school|professional-school)/[^/]+\.html$",
    "research_center": r"/research-centers/[^/]+\.html$",
}

# CSS Selectors for different page types
SELECTORS = {
    # Person profile page selectors
    "person": {
        "name": ["h1.person-name", "h1", ".page-title h1"],
        "title": [".person-title", ".academic-title"],
        "email": ["a[href^='mailto:']", ".email a"],
        "phone": [".phone", ".tel", "a[href^='tel:']"],
        "office": [".office", ".room", ".location"],
        "institute": [".institute", ".organization", ".affiliation"],
        "image": [".person-image img", ".profile-image img"],
    },
    
    # Institute page selectors
    "institute": {
        "name": ["h1", ".page-title"],
        "description": [".teaser", ".description", ".intro"],
        "staff_link": ["a[href*='team']", "a[href*='members']", "a[href*='staff']"],
        "professors": [".professors", ".team-professors"],
    },
    
    # School page selectors
    "school": {
        "name": ["h1", ".page-title"],
        "description": [".teaser", ".description"],
        "institutes_link": ["a[href*='institutes']"],
        "dean": [".dean", ".leadership"],
    },
    
    # Staff list page selectors
    "staff_list": {
        "person_link": [
            "a[href*='/universitaet/person/']",
            "a[href*='/university/person/']",
            ".person-list a",
            ".staff-list a",
        ],
        "person_name": [".person-name", ".name", "a"],
        "person_category": [".category", ".person-category"],
    },
    
    # Program page selectors
    "program": {
        "name": ["h1", ".program-title"],
        "description": [".description", ".teaser"],
        "duration": [".duration", ".study-duration"],
        "degree": [".degree", ".qualification"],
    },
}

# School/Faculty mapping with their institutes (with actual URLs)
SCHOOLS_STRUCTURE = {
    "School of Education": {
        "url": "/en/institutions/faculty/education.html",
        "institutes": {
            "Institute of Educational Sciences (IBIWI)": "/en/institutes/ibiwi.html",
            "Institute of English Studies (IES)": "/en/institutes/ies.html",
            "Institute of Ethics and Theological Research (IET)": "/en/institutes/iet.html",
            "Institute for Exercise, Sport and Health (IBSG)": "/en/institutes/ibsg.html",
            "Institute of Fine Arts, Music and Education (IKMV)": "/en/institutes/ikmv.html",
            "Institute of German Language and Literature Studies (IDD)": "/en/institutes/idd.html",
            "Institute of Mathematics and its Didactics (IMD)": None,
            "Institute of Psychology in Education (IPE)": "/en/institutes/ipe.html",
            "Institute of Social Work and Social Pedagogy (IFSP)": "/en/institutes/ifsp.html",
            "Institute of Social Science Education (ISWB)": "/en/institutes/iswb.html",
        }
    },
    "School of Culture and Society": {
        "url": "/en/institutions/faculty/humanities-social-sciences.html",
        "institutes": {
            "Institute of Culture and Aesthetics of Digital Media (ICAM)": "/en/institutes/icam.html",
            "Institute of History and Literary Cultures (IGL)": "/en/institutes/igl.html",
            "Institute of Urban and Cultural Area Research (IFSK)": "/en/institutes/ifsk.html",
            "Institute of Philosophy and Art History (IPK)": "/en/institutes/ipk.html",
            "Institute of Sociology and Cultural Organization (ISCO)": "/en/institutes/isco.html",
        }
    },
    "School of Management and Technology": {
        "url": "/en/institutions/faculty/management-and-technology.html",
        "institutes": {
            "Institute for Auditing & Tax (IAT)": "/en/institutes/iat.html",
            "Institute of New Venture Management (IGM)": "/en/institutes/institute-of-new-venture-management.html",
            "Institute of Information Systems (IIS)": "/en/institutes/iis.html",
            "Institute of Experimental Industrial Psychology - LüneLab": "/en/institutes/luenelab.html",
            "Institute of Knowledge and Information Management (IWI)": "/en/institutes/iwi.html",
            "Institute for Management and Organisation (IMO)": "/en/institutes/imo.html",
            "Institute of Management, Accounting & Finance (IMAF)": "/en/institutes/imaf.html",
            "Institute of Marketing (IFM)": "/en/institutes/ifm.html",
            "Institute of Performance Management (IPM)": None,
            "Institute for Production Technology and Systems (IPTS)": "/en/institutes/ipts.html",
        }
    },
    "School of Sustainability": {
        "url": "/en/institutions/faculty/sustainability.html",
        "institutes": {
            "Centre for Sustainability Management (CSM)": "/en/institutes/centre-for-sustainability-management-csm.html",
            "Institute of Ecology (IE)": "/en/institutes/institute-of-ecology.html",
            "Institute of Ethics and Transdisciplinary Sustainability Research (IETSR)": "/en/institutes/ietsr.html",
            "Institute of Sustainability Psychology (ISP)": "/en/institutes/isep.html",
            "Institute of Sustainable Chemistry (INSC)": "/en/institutes/insc.html",
            "Institute of Sustainability Governance (INSUGO)": "/en/institutes/insugo.html",
            "Social-Ecological Systems Institute (SESI)": "/en/institutes/sesi.html",
            "Sustainability Education and Transdisciplinary Research Institute (SETRI)": "/en/institutes/setri.html",
        }
    },
    "School of Public Affairs": {
        "url": "/en/institutions/faculty/school-of-public-affairs.html",
        "institutes": {
            "Institute of Political Science (IPW)": "/en/institutes/ipw.html",
            "Leuphana Law School (LLS)": "/en/institutes/lls.html",
            "Institute of Economics (IVWL)": "/en/institutes/ivwl.html",
        }
    },
}

# Staff categories
STAFF_CATEGORIES = [
    "Professors",
    "Junior Professors",
    "Assistant Professors",
    "Visiting Professors",
    "Honorary Professors",
    "Emeritus Professors",
    "Retired Professors",
    "Adjunct Professors",
    "Research Assistants",
    "Post-Doc Scholars",
    "PhD Scholars",
    "Lecturers",
    "Visiting Scientists",
    "Technical and Administrative Staff",
]

# Request configuration
REQUEST_CONFIG = {
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 2,
    "concurrent_requests": 5,
    "request_delay": 1,  # Delay between requests in seconds
}

# Respect robots.txt - these paths are disallowed
DISALLOWED_PATHS = [
    "/seite/",
    "/page/",
    "/intranet/",
    "/interner-bereich/",
    "/testsite/",
    "/test-und-demoseiten/",
    "/fileadmin/user_upload/INTRANET/",
]

# Output configuration
OUTPUT_CONFIG = {
    "raw_json_dir": "data/raw",
    "rdf_dir": "data/rdf",
    "csv_dir": "data/csv",
}

# Ontology namespace
ONTOLOGY_NS = "http://leuphana.de/ontology#"
INSTANCE_NS = "http://leuphana.de/resource/"

# Chair/Professorship URL patterns (from sitemap analysis)
CHAIR_URL_PATTERNS = [
    # Law School professorship pages
    r"https://www\.leuphana\.de/institute/lls/professuren/[^/]+/[^/]+\.html$",
    # IPK professorship pages (philosophy, art history)
    r"https://www\.leuphana\.de/institute/ipk/[^/]+/professur-fuer-[^/]+\.html$",
    # IGL professorship pages (literary cultures)
    r"https://www\.leuphana\.de/institute/igl/[^/]+/professur-fuer-[^/]+\.html$",
    # UNESCO Chair
    r"https://www\.leuphana\.de/portale/unesco-chair\.html$",
]

# Professorship URLs (Chair/Lehrstuhl pages)
# These are populated dynamically from institute pages during scraping
PROFESSORSHIP_URLS = {}

# Person URL patterns found in sitemap (German URLs)
PERSON_URL_PATTERNS = [
    r"https://www\.leuphana\.de/universitaet/personen/[a-z\-]+\.html$",
    r"https://www\.leuphana\.de/institute/[^/]+/personen/[a-z\-]+\.html$",
    r"https://www\.leuphana\.de/zentren/[^/]+/personen/[a-z\-]+\.html$",
    r"https://www\.leuphana\.de/college/kontakt/[a-z\-]+\.html$",
]

# Minor program URL pattern
MINOR_URL_PATTERN = r"https://www\.leuphana\.de/college/bachelor/minor-[^/]+\.html$"

# Research center (Zentren) URL pattern
RESEARCH_CENTER_URL_PATTERN = r"https://www\.leuphana\.de/zentren/[^/]+\.html$"

# Research project URL patterns
RESEARCH_PROJECT_PATTERNS = [
    r".*/forschung-projekte/[^/]+\.html$",
    r".*/drittmittelprojekte/[^/]+\.html$",
]

# Bachelor program URL pattern (excluding minors)
BACHELOR_PROGRAM_PATTERN = r"https://www\.leuphana\.de/college/bachelor/[^/]+\.html$"

# Course catalog URL patterns
COURSE_URL_PATTERNS = [
    r".*/vorlesungsverzeichnis/.*\.html$",
]
