#!/usr/bin/env python3
"""
Leuphana University Knowledge Graph - Web Scraper

This module scrapes the Leuphana University website to extract information
about schools, institutes, professors, staff, and programs.

Author: Bachelor's Thesis Project
Supervisor: Debayan Banerjee
"""

import asyncio
import json
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from urllib.parse import urljoin, urlparse

import aiohttp
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

import sys
from pathlib import Path
# Add parent directory to path for imports when running directly
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from config import (
    BASE_URL, BASE_URL_EN, SEED_URLS, SELECTORS, SCHOOLS_STRUCTURE,
    REQUEST_CONFIG, DISALLOWED_PATHS, OUTPUT_CONFIG, STAFF_CATEGORIES,
    PROFESSORSHIP_URLS, PERSON_URL_PATTERNS, MINOR_URL_PATTERN,
    RESEARCH_CENTER_URL_PATTERN, RESEARCH_PROJECT_PATTERNS,
    CHAIR_URL_PATTERNS, BACHELOR_PROGRAM_PATTERN
)


# ============================================================================
# Data Classes for Extracted Entities
# ============================================================================

@dataclass
class Person:
    """Represents a person (professor, staff member, etc.)"""
    uri: str
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None  # Dr., Prof. Dr., etc.
    category: Optional[str] = None  # Professor, Research Assistant, etc.
    email: Optional[str] = None
    phone: Optional[str] = None
    office: Optional[str] = None
    webpage: Optional[str] = None
    institute: Optional[str] = None
    school: Optional[str] = None
    research_areas: List[str] = field(default_factory=list)
    image_url: Optional[str] = None
    source_url: str = ""


@dataclass
class Organization:
    """Represents an organization (school, institute, research center)"""
    uri: str
    name: str
    org_type: str  # School, Institute, ResearchCenter, etc.
    abbreviation: Optional[str] = None
    description: Optional[str] = None
    parent: Optional[str] = None  # URI of parent organization
    webpage: Optional[str] = None
    address: Optional[str] = None
    members: List[str] = field(default_factory=list)  # URIs of members
    source_url: str = ""


@dataclass
class StudyProgram:
    """Represents a study program (Bachelor, Master, etc.)"""
    uri: str
    name: str
    program_type: str  # BachelorProgram, MasterProgram, DoctoralProgram
    description: Optional[str] = None
    duration: Optional[str] = None
    language: Optional[str] = None
    offered_by: Optional[str] = None  # URI of offering organization
    webpage: Optional[str] = None
    source_url: str = ""


@dataclass
class Chair:
    """Represents a Chair/Professorship (Lehrstuhl) - an organizational unit headed by a professor"""
    uri: str
    name: str
    description: Optional[str] = None
    parent: Optional[str] = None  # URI of parent organization (Institute)
    headed_by: Optional[str] = None  # URI of the professor heading this chair
    webpage: Optional[str] = None
    team_members: List[str] = field(default_factory=list)  # URIs of team members
    source_url: str = ""


@dataclass
class HiwiPosition:
    """Represents a Student Assistant (Hiwi) position posting"""
    uri: str
    title: str
    description: Optional[str] = None
    department: Optional[str] = None  # Which institute/department posted it
    contact_person: Optional[str] = None  # Contact person URI
    contact_email: Optional[str] = None
    posted_date: Optional[str] = None
    hours_per_week: Optional[str] = None
    webpage: Optional[str] = None
    source_url: str = ""


@dataclass
class Course:
    """Represents a Course/Module in a study program"""
    uri: str
    name: str
    description: Optional[str] = None
    credit_points: Optional[int] = None
    course_type: Optional[str] = None  # Lecture, Seminar, Tutorial, etc.
    part_of_program: Optional[str] = None  # URI of the program
    taught_by: List[str] = field(default_factory=list)  # URIs of instructors
    semester: Optional[str] = None  # Which semester (1st, 2nd, etc.)
    language: Optional[str] = None
    webpage: Optional[str] = None
    source_url: str = ""


@dataclass
class Minor:
    """Represents a Minor (Nebenfach) study field."""
    uri: str
    name: str
    name_de: Optional[str] = None  # German name
    description: Optional[str] = None
    credit_points: Optional[int] = None
    part_of_program: Optional[str] = None  # URI of Bachelor program
    offered_by: Optional[str] = None  # URI of College
    webpage: Optional[str] = None
    source_url: str = ""


@dataclass
class ResearchProject:
    """Represents a Research Project."""
    uri: str
    name: str
    description: Optional[str] = None
    conducted_by: Optional[str] = None  # URI of organization (Institute/Center)
    principal_investigator: Optional[str] = None  # URI of Person
    funding_source: Optional[str] = None  # e.g., "DFG", "EU", etc.
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    webpage: Optional[str] = None
    source_url: str = ""


# ============================================================================
# Helper Functions
# ============================================================================

def create_uri(entity_type: str, name: str) -> str:
    """Create a URI for an entity based on type and name."""
    # Clean the name for URI
    clean_name = re.sub(r'[^\w\s-]', '', name.lower())
    clean_name = re.sub(r'[\s]+', '-', clean_name.strip())
    clean_name = re.sub(r'-+', '-', clean_name)
    return f"http://leuphana.de/resource/{entity_type}/{clean_name}"


def is_allowed_url(url: str) -> bool:
    """Check if URL is allowed according to robots.txt rules."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    for disallowed in DISALLOWED_PATHS:
        if disallowed.lower() in path:
            return False
    return True


def extract_email(soup: BeautifulSoup) -> Optional[str]:
    """Extract email address from page."""
    for selector in SELECTORS["person"]["email"]:
        elem = soup.select_one(selector)
        if elem:
            href = elem.get("href", "")
            if href.startswith("mailto:"):
                return href.replace("mailto:", "").split("?")[0].strip()
            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', elem.get_text())
            if email_match:
                return email_match.group()
    
    # Also try to find email in text
    text = soup.get_text()
    email_match = re.search(r'[\w\.-]+@leuphana\.de', text)
    if email_match:
        return email_match.group()
    
    return None


def extract_phone(soup: BeautifulSoup) -> Optional[str]:
    """Extract phone number from page."""
    for selector in SELECTORS["person"]["phone"]:
        elem = soup.select_one(selector)
        if elem:
            href = elem.get("href", "")
            if href.startswith("tel:"):
                return href.replace("tel:", "").strip()
            phone_match = re.search(r'[\d\s\-\+\/\.]{10,}', elem.get_text())
            if phone_match:
                return phone_match.group().strip()
    
    # Try to find phone in text (German format)
    text = soup.get_text()
    phone_match = re.search(r'04131[-\s]?677[-\s]?\d{4}', text)
    if phone_match:
        return phone_match.group()
    
    return None


def extract_name_parts(full_name: str) -> tuple:
    """Extract first name, last name, and title from full name."""
    # Common academic titles
    titles = ['Prof.', 'Dr.', 'Dr.-Ing.', 'Jun.-Prof.', 'Apl.', 'rer.', 'nat.', 
              'phil.', 'habil.', 'PD', 'M.A.', 'M.Sc.', 'MBA', 'LL.M.', 'Dipl.-']
    
    title_parts = []
    name_parts = full_name.split()
    
    # Extract titles
    while name_parts and any(name_parts[0].startswith(t) or name_parts[0] == t for t in titles):
        title_parts.append(name_parts.pop(0))
    
    title = ' '.join(title_parts) if title_parts else None
    
    # Remaining parts are the name
    if len(name_parts) >= 2:
        first_name = ' '.join(name_parts[:-1])
        last_name = name_parts[-1]
    elif len(name_parts) == 1:
        first_name = None
        last_name = name_parts[0]
    else:
        first_name = None
        last_name = full_name
    
    return first_name, last_name, title


def determine_person_category(text: str, url: str = "", title: str = "") -> str:
    """Determine the category of a person based on available text, URL, and title.

    Args:
        text: Text content from page or name
        url: Profile URL
        title: Academic title (e.g., "Prof. Dr.")

    Returns:
        Category string matching ontology classes
    """
    # Combine all available text for matching
    combined = f"{text} {url} {title}".lower()

    # Check from most specific to most general
    if 'juniorprof' in combined or 'junior professor' in combined or 'jun.-prof' in combined:
        return 'JuniorProfessor'
    elif 'honorar' in combined or 'honorary' in combined:
        return 'HonoraryProfessor'
    elif 'emerit' in combined:
        return 'EmeritusProfessor'
    elif 'gastprof' in combined or 'visiting prof' in combined:
        return 'VisitingProfessor'
    elif 'apl.' in combined or 'adjunct' in combined or 'außerplanmäßig' in combined:
        return 'AdjunctProfessor'
    elif 'prof.' in combined or 'professor' in combined:
        return 'Professor'
    elif 'post-doc' in combined or 'postdoc' in combined:
        return 'PostDoc'
    elif 'phd' in combined or 'doktorand' in combined or 'doctoral' in combined:
        return 'PhDStudent'
    elif 'lecturer' in combined or 'lektor' in combined or 'lehrbeauft' in combined:
        return 'Lecturer'
    elif 'research assistant' in combined or 'wissenschaftl' in combined:
        return 'ResearchAssistant'
    elif 'visiting scientist' in combined or 'gastwissenschaft' in combined:
        return 'VisitingScientist'
    elif 'hiwi' in combined or 'student assistant' in combined or 'hilfskraft' in combined:
        return 'StudentAssistant'
    elif 'dr.' in combined and 'prof' not in combined:
        # Has doctorate but not professor - likely PostDoc or ResearchAssistant
        return 'PostDoc'
    else:
        return 'AcademicStaff'


# ============================================================================
# Main Scraper Class
# ============================================================================

class LeuphanaScaper:
    """
    Web scraper for Leuphana University.
    
    Extracts information about:
    - Schools (Faculties)
    - Institutes
    - Professors and Staff
    - Study Programs
    - Research Centers
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.visited_urls: Set[str] = set()
        self.persons: Dict[str, Person] = {}
        self.organizations: Dict[str, Organization] = {}
        self.programs: Dict[str, StudyProgram] = {}
        self.chairs: Dict[str, Chair] = {}  # Store Chair/Professorship entities
        self.hiwi_positions: Dict[str, HiwiPosition] = {}  # Store Hiwi position postings
        self.courses: Dict[str, Course] = {}  # Store Course/Module entities
        self.minors: Dict[str, Minor] = {}  # Store Minor programs
        self.research_projects: Dict[str, ResearchProject] = {}  # Store Research Projects

        # Create output directories
        for dir_name in OUTPUT_CONFIG.values():
            Path(dir_name).mkdir(parents=True, exist_ok=True)
    
    def get_soup(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch URL and return BeautifulSoup object (synchronous)."""
        if not is_allowed_url(url):
            print(f"Skipping disallowed URL: {url}")
            return None

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; LeuphanaKGBot/1.0; Bachelor Thesis Project)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5,de;q=0.3',
            }

            response = requests.get(
                url,
                headers=headers,
                timeout=REQUEST_CONFIG["timeout"]
            )
            response.raise_for_status()

            return BeautifulSoup(response.content, 'lxml')

        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def fetch_person_details(self, url: str) -> Dict[str, Any]:
        """Fetch details from a person's profile page.

        Args:
            url: Profile page URL

        Returns:
            Dictionary with extracted details (email, phone, title, etc.)
        """
        if not url or url in self.visited_urls:
            return {}

        full_url = urljoin(BASE_URL, url) if not url.startswith('http') else url

        # Skip non-profile URLs
        if '/person/' not in full_url and '/team/' not in full_url:
            return {}

        soup = self.get_soup(full_url)
        if not soup:
            return {}

        self.visited_urls.add(full_url)
        details = {}

        # Get page text for category detection (limited to avoid memory issues)
        page_text = soup.get_text()[:2000]
        details["page_text"] = page_text

        # Extract title from page heading
        for selector in SELECTORS["person"]["name"]:
            elem = soup.select_one(selector)
            if elem:
                name_text = elem.get_text(strip=True)
                _, _, title = extract_name_parts(name_text)
                if title:
                    details["title"] = title
                break

        # Extract email
        email = extract_email(soup)
        if email:
            details["email"] = email

        # Extract phone
        phone = extract_phone(soup)
        if phone:
            details["phone"] = phone

        # Extract office/room
        for selector in SELECTORS["person"]["office"]:
            elem = soup.select_one(selector)
            if elem:
                details["office"] = elem.get_text(strip=True)
                break

        # Extract research areas
        research_areas = []
        # Look for research interests section
        for keyword in ['research', 'forschung', 'interest', 'area', 'focus']:
            sections = soup.find_all(['div', 'section', 'ul'],
                                    class_=re.compile(keyword, re.I))
            for section in sections:
                items = section.find_all('li')
                for item in items[:5]:  # Limit to 5 research areas
                    text = item.get_text(strip=True)
                    if len(text) > 3 and len(text) < 100:
                        research_areas.append(text)

        if research_areas:
            details["research_areas"] = research_areas[:5]

        # Be polite to the server
        time.sleep(0.3)

        return details
    
    def scrape_school(self, name: str, url: str) -> Organization:
        """Scrape a school (faculty) page."""
        full_url = urljoin(BASE_URL, url)
        print(f"Scraping school: {name}")
        
        soup = self.get_soup(full_url)
        description = None
        
        if soup:
            # Try to get description
            for selector in SELECTORS["school"]["description"]:
                elem = soup.select_one(selector)
                if elem:
                    description = elem.get_text(strip=True)[:500]
                    break
        
        school = Organization(
            uri=create_uri("school", name),
            name=name,
            org_type="School",
            description=description,
            parent="http://leuphana.de/resource/university/leuphana",
            webpage=full_url,
            source_url=full_url
        )
        
        self.organizations[school.uri] = school
        return school
    
    def scrape_institute(self, name: str, school_name: str, institute_url: str = None) -> Organization:
        """Scrape institute page to extract description, research areas, and team members."""
        # Extract abbreviation if present
        abbrev_match = re.search(r'\(([A-Z]+)\)', name)
        abbreviation = abbrev_match.group(1) if abbrev_match else None

        description = None
        research_areas = []
        team_members = []

        # If we have a URL, scrape the institute page
        if institute_url:
            full_url = urljoin(BASE_URL, institute_url)
            print(f"    Scraping institute page: {full_url}")
            soup = self.get_soup(full_url)

            if soup:
                # Extract description from meta or first paragraph
                meta_desc = soup.find('meta', attrs={'name': 'description'})
                if meta_desc:
                    description = meta_desc.get('content', '')[:500]

                if not description:
                    # Try to find intro/teaser text
                    intro = soup.find('div', class_=['teaser', 'intro', 'description'])
                    if intro:
                        description = intro.get_text(strip=True)[:500]
                    else:
                        # Get first substantial paragraph
                        for p in soup.find_all('p'):
                            text = p.get_text(strip=True)
                            if len(text) > 100:
                                description = text[:500]
                                break

                # Extract team member links from team pages
                team_links = soup.find_all('a', href=re.compile(r'/team/|/members/'))
                for link in team_links:
                    href = link.get('href', '')
                    if href and 'team' in href:
                        member_name = link.get_text(strip=True)
                        if member_name and len(member_name) > 2:
                            member_url = urljoin(full_url, href)
                            team_members.append((member_name, member_url))

                # Also look for person links directly on the page
                person_sections = soup.find_all(['div', 'section'], class_=re.compile(r'team|staff|members|persons'))
                for section in person_sections:
                    for link in section.find_all('a'):
                        href = link.get('href', '')
                        name_text = link.get_text(strip=True)
                        if name_text and len(name_text) > 2 and not any(skip in name_text.lower() for skip in ['more', 'read', 'contact', 'email']):
                            team_members.append((name_text, urljoin(full_url, href) if href else None))

        webpage = urljoin(BASE_URL, institute_url) if institute_url else f"{BASE_URL_EN}/institutes/{abbreviation.lower() if abbreviation else 'unknown'}.html"

        institute = Organization(
            uri=create_uri("institute", name),
            name=name,
            org_type="Institute",
            abbreviation=abbreviation,
            description=description,
            parent=create_uri("school", school_name),
            webpage=webpage,
            members=[m[0] for m in team_members[:20]],  # Store member names
            source_url=webpage
        )

        self.organizations[institute.uri] = institute

        # Create person entities for team members
        for member_name, member_url in team_members[:15]:  # Limit to first 15 per institute
            if member_name and member_name not in [p.name for p in self.persons.values()]:
                first_name, last_name, title = extract_name_parts(member_name)

                # Try to fetch profile page for more details
                person_details = self.fetch_person_details(member_url) if member_url else {}

                # Use profile title if available
                if person_details.get("title"):
                    title = person_details["title"]

                # Determine category using all available info
                category = determine_person_category(
                    text=member_name + " " + (person_details.get("page_text", "") or ""),
                    url=member_url or "",
                    title=title or ""
                )

                person = Person(
                    uri=create_uri("person", member_name),
                    name=member_name,
                    first_name=first_name,
                    last_name=last_name,
                    title=title,
                    category=category,
                    email=person_details.get("email"),
                    phone=person_details.get("phone"),
                    office=person_details.get("office"),
                    institute=name,
                    school=school_name,
                    webpage=member_url,
                    research_areas=person_details.get("research_areas", []),
                    source_url=webpage
                )
                self.persons[person.uri] = person

        return institute
    
    def scrape_person_list_page(self, url: str, category: str = None) -> List[Person]:
        """Scrape a page listing multiple persons."""
        full_url = urljoin(BASE_URL, url) if not url.startswith('http') else url
        print(f"Scraping person list: {full_url}")
        
        soup = self.get_soup(full_url)
        if not soup:
            return []
        
        persons = []
        
        # Find person links
        for selector in SELECTORS["staff_list"]["person_link"]:
            links = soup.select(selector)
            for link in links:
                href = link.get('href', '')
                if not href:
                    continue
                
                person_url = urljoin(full_url, href)
                
                # Skip if already visited or disallowed
                if person_url in self.visited_urls or not is_allowed_url(person_url):
                    continue
                
                # Extract name from link text
                name = link.get_text(strip=True)
                if not name or len(name) < 3:
                    continue
                
                # Create person entity
                first_name, last_name, title = extract_name_parts(name)
                person_category = category or determine_person_category(name, person_url, title or "")

                person = Person(
                    uri=create_uri("person", name),
                    name=name,
                    first_name=first_name,
                    last_name=last_name,
                    title=title,
                    category=person_category,
                    webpage=person_url,
                    source_url=full_url
                )

                # Try to extract email if visible on list
                email_elem = link.find_parent().find('a', href=re.compile(r'mailto:'))
                if email_elem:
                    person.email = email_elem['href'].replace('mailto:', '').split('?')[0]

                persons.append(person)
                self.persons[person.uri] = person
                self.visited_urls.add(person_url)

                # Be polite to the server
                time.sleep(0.5)
        
        return persons
    
    def scrape_person_profile(self, url: str) -> Optional[Person]:
        """Scrape detailed person profile page."""
        full_url = urljoin(BASE_URL, url) if not url.startswith('http') else url
        
        if full_url in self.visited_urls:
            return None
        
        soup = self.get_soup(full_url)
        if not soup:
            return None
        
        self.visited_urls.add(full_url)
        
        # Extract name
        name = None
        for selector in SELECTORS["person"]["name"]:
            elem = soup.select_one(selector)
            if elem:
                name = elem.get_text(strip=True)
                break
        
        if not name:
            return None
        
        first_name, last_name, title = extract_name_parts(name)
        
        # Extract other details
        email = extract_email(soup)
        phone = extract_phone(soup)
        
        # Extract office
        office = None
        for selector in SELECTORS["person"]["office"]:
            elem = soup.select_one(selector)
            if elem:
                office = elem.get_text(strip=True)
                break
        
        # Determine category
        page_text = soup.get_text()
        category = determine_person_category(page_text, full_url)
        
        # Extract institute affiliation
        institute = None
        for selector in SELECTORS["person"]["institute"]:
            elem = soup.select_one(selector)
            if elem:
                institute = elem.get_text(strip=True)
                break
        
        person = Person(
            uri=create_uri("person", name),
            name=name,
            first_name=first_name,
            last_name=last_name,
            title=title,
            category=category,
            email=email,
            phone=phone,
            office=office,
            webpage=full_url,
            institute=institute,
            source_url=full_url
        )
        
        self.persons[person.uri] = person
        return person
    
    def scrape_all_schools(self):
        """Scrape all schools from the known structure."""
        print("\n=== Scraping Schools ===")
        for school_name, school_data in SCHOOLS_STRUCTURE.items():
            school = self.scrape_school(school_name, school_data["url"])

            # Scrape institutes (now a dict with URLs)
            print(f"  Scraping institutes for {school_name}")
            institutes = school_data["institutes"]
            for institute_name, institute_url in institutes.items():
                self.scrape_institute(institute_name, school_name, institute_url)
                time.sleep(REQUEST_CONFIG["request_delay"])

            time.sleep(REQUEST_CONFIG["request_delay"])
    
    def scrape_staff_directories(self):
        """Scrape staff from main directories."""
        print("\n=== Scraping Staff Directories ===")

        # Scrape all configured staff directory pages
        if "staff" in SEED_URLS:
            for staff_type, url in SEED_URLS["staff"].items():
                print(f"Scraping {staff_type}...")
                self.scrape_person_list_page(url)
                time.sleep(REQUEST_CONFIG["request_delay"])

    def scrape_professorships(self):
        """Scrape Chair/Professorship pages to extract chairs and their heads.
        
        This creates:
        - Chair entities (organizational units)
        - heads relationship between Professor and Chair
        - memberOf relationships for team members
        """
        print("\n=== Scraping Professorships (Chairs) ===")
        
        for institute_key, professorship_urls in PROFESSORSHIP_URLS.items():
            print(f"\nScraping professorships for {institute_key.upper()}")
            
            for prof_key, url in professorship_urls.items():
                print(f"  Checking: {prof_key} - {url}")
                soup = self.get_soup(url)
                if not soup:
                    continue
                
                self.visited_urls.add(url)
                
                # Find links to individual professorship pages
                # Pattern: /professorships/[area]/[specific-professorship].html
                prof_links = []
                
                # Look for professorship links in navigation or content
                for link in soup.find_all('a', href=True):
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Look for links that look like professorship pages
                    if '/professorships/' in href and href.endswith('.html'):
                        # Skip the current page and category pages
                        if href != url and text and len(text) > 10:
                            if 'professorship' in text.lower() or 'law' in text.lower() or 'public' in text.lower():
                                full_url = urljoin(BASE_URL, href)
                                if full_url not in self.visited_urls:
                                    prof_links.append((text, full_url))
                
                # Also check for section headers that might indicate professorships
                # Look for patterns like "Professorship for X" or "Professorship of X"
                for heading in soup.find_all(['h2', 'h3', 'h4']):
                    heading_text = heading.get_text(strip=True)
                    if 'professorship' in heading_text.lower():
                        # Try to find associated professor name
                        prof_name = None
                        next_elem = heading.find_next(['p', 'div', 'ul'])
                        if next_elem:
                            # Look for "Prof. Dr." pattern
                            text = next_elem.get_text()
                            prof_match = re.search(r'(Prof\.\s*Dr\.[^,\n]+)', text)
                            if prof_match:
                                prof_name = prof_match.group(1).strip()
                        
                        # Create chair entity directly
                        self._create_chair_from_heading(heading_text, prof_name, url, institute_key)
                
                # Process individual professorship pages
                for prof_name, prof_url in prof_links:
                    self._scrape_single_professorship(prof_name, prof_url, institute_key)
                    time.sleep(0.5)
                
                time.sleep(REQUEST_CONFIG["request_delay"])
    
    def _create_chair_from_heading(self, chair_name: str, professor_name: str, source_url: str, institute_key: str):
        """Create a Chair entity from a heading found on a page."""
        # Clean up chair name
        chair_name = chair_name.strip()
        if not chair_name or len(chair_name) < 10:
            return
        
        # Skip if already exists
        chair_uri = create_uri("chair", chair_name)
        if chair_uri in self.chairs:
            return
        
        # Find parent institute
        parent_uri = None
        for inst_uri, inst in self.organizations.items():
            if inst.org_type == "Institute" and institute_key.upper() in inst.name.upper():
                parent_uri = inst_uri
                break
        
        # Find or create the professor
        headed_by_uri = None
        if professor_name:
            # Check if professor already exists
            for person_uri, person in self.persons.items():
                if person.name == professor_name or professor_name in person.name:
                    headed_by_uri = person_uri
                    break
            
            # Create new professor if not found
            if not headed_by_uri:
                first_name, last_name, title = extract_name_parts(professor_name)
                professor = Person(
                    uri=create_uri("person", professor_name),
                    name=professor_name,
                    first_name=first_name,
                    last_name=last_name,
                    title=title,
                    category="Professor",
                    source_url=source_url
                )
                self.persons[professor.uri] = professor
                headed_by_uri = professor.uri
        
        # Create chair entity
        chair = Chair(
            uri=chair_uri,
            name=chair_name,
            parent=parent_uri,
            headed_by=headed_by_uri,
            webpage=source_url,
            source_url=source_url
        )
        self.chairs[chair.uri] = chair
        print(f"    Created chair: {chair_name[:50]}... (headed by: {professor_name or 'Unknown'})")
    
    def _scrape_single_professorship(self, chair_name: str, url: str, institute_key: str):
        """Scrape a single professorship page to extract chair details and team."""
        soup = self.get_soup(url)
        if not soup:
            return
        
        self.visited_urls.add(url)
        
        # Get page title as chair name if not provided
        if not chair_name:
            h1 = soup.find('h1')
            if h1:
                chair_name = h1.get_text(strip=True)
        
        if not chair_name or len(chair_name) < 5:
            return
        
        # Skip if already exists
        chair_uri = create_uri("chair", chair_name)
        if chair_uri in self.chairs:
            return
        
        # Get description
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')[:500]
        
        # Find parent institute
        parent_uri = None
        for inst_uri, inst in self.organizations.items():
            if inst.org_type == "Institute" and institute_key.upper() in inst.name.upper():
                parent_uri = inst_uri
                break
        
        # Find the chair holder (usually under "Professorship holder" or similar heading)
        headed_by_uri = None
        team_member_uris = []
        
        # Look for team section
        team_section = soup.find(['div', 'section'], class_=re.compile(r'team|staff|members', re.I))
        if not team_section:
            # Try finding by heading
            for heading in soup.find_all(['h2', 'h3']):
                if 'team' in heading.get_text().lower():
                    team_section = heading.find_parent(['div', 'section'])
                    break
        
        # Parse team members from the page
        page_text = soup.get_text()
        
        # Look for "Professorship holder" section
        holder_patterns = [
            r'Professorship holder[:\s]*([^\n]+)',
            r'Chair holder[:\s]*([^\n]+)',
            r'Professor[:\s]*(Prof\.[^\n]+)',
        ]
        
        for pattern in holder_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                holder_name = match.group(1).strip()
                # Clean up the name
                holder_name = re.sub(r'\s+', ' ', holder_name)
                holder_name = holder_name.split('\n')[0].strip()
                
                if holder_name and len(holder_name) > 3:
                    # Find or create the professor
                    for person_uri, person in self.persons.items():
                        if holder_name in person.name or person.name in holder_name:
                            headed_by_uri = person_uri
                            break
                    
                    if not headed_by_uri:
                        first_name, last_name, title = extract_name_parts(holder_name)
                        professor = Person(
                            uri=create_uri("person", holder_name),
                            name=holder_name,
                            first_name=first_name,
                            last_name=last_name,
                            title=title,
                            category="Professor",
                            webpage=url,
                            source_url=url
                        )
                        self.persons[professor.uri] = professor
                        headed_by_uri = professor.uri
                    break
        
        # Extract team members (research associates, assistants, etc.)
        team_patterns = [
            (r'Research Associate[s]?[:\s]*([^\n]+)', 'ResearchAssistant'),
            (r'Research Assistant[s]?[:\s]*([^\n]+)', 'ResearchAssistant'),
            (r'Student assistant[s]?[:\s]*([^\n]+)', 'StudentAssistant'),
            (r'Secretariat[:\s]*([^\n]+)', 'AdministrativeStaff'),
        ]
        
        for pattern, category in team_patterns:
            matches = re.findall(pattern, page_text, re.I)
            for match in matches:
                # Split by common separators
                names = re.split(r'[,;•·]', match)
                for name in names:
                    name = name.strip()
                    # Skip empty or too short names
                    if not name or len(name) < 3:
                        continue
                    # Skip if it looks like a section header
                    if any(skip in name.lower() for skip in ['research', 'assistant', 'student', 'former', 'staff']):
                        continue
                    
                    # Check if person already exists
                    existing = False
                    for person_uri, person in self.persons.items():
                        if name in person.name or person.name in name:
                            team_member_uris.append(person_uri)
                            existing = True
                            break
                    
                    if not existing:
                        first_name, last_name, title = extract_name_parts(name)
                        person = Person(
                            uri=create_uri("person", name),
                            name=name,
                            first_name=first_name,
                            last_name=last_name,
                            title=title,
                            category=category,
                            source_url=url
                        )
                        self.persons[person.uri] = person
                        team_member_uris.append(person.uri)
        
        # Create chair entity
        chair = Chair(
            uri=chair_uri,
            name=chair_name,
            description=description,
            parent=parent_uri,
            headed_by=headed_by_uri,
            webpage=url,
            team_members=team_member_uris,
            source_url=url
        )
        self.chairs[chair.uri] = chair
        
        headed_by_name = "Unknown"
        if headed_by_uri:
            for p in self.persons.values():
                if p.uri == headed_by_uri:
                    headed_by_name = p.name
                    break
        
        print(f"    Created chair: {chair_name[:60]}...")
        print(f"      Headed by: {headed_by_name}")
        print(f"      Team members: {len(team_member_uris)}")

    def scrape_chairs_from_sitemap(self, sitemap_urls: List[str]):
        """Scrape Chair/Professorship pages from sitemap URLs.

        This extracts chairs (Lehrstuhl/Professur) as distinct organizational units.
        Each chair is typically headed by a professor and belongs to an institute.
        """
        print("\n=== Scraping Chairs from Sitemap ===")

        # Filter URLs matching chair patterns
        chair_urls = []
        for url in sitemap_urls:
            for pattern in CHAIR_URL_PATTERNS:
                if re.match(pattern, url):
                    chair_urls.append(url)
                    break

        print(f"  Found {len(chair_urls)} chair/professorship URLs in sitemap")

        for url in tqdm(chair_urls, desc="Scraping chairs"):
            if url in self.visited_urls:
                continue

            self._scrape_chair_page(url)
            time.sleep(REQUEST_CONFIG["request_delay"] / 2)

    def _scrape_chair_page(self, url: str):
        """Scrape a single chair/professorship page."""
        soup = self.get_soup(url)
        if not soup:
            return

        self.visited_urls.add(url)

        # Get chair name from page title
        h1 = soup.find('h1')
        chair_name = h1.get_text(strip=True) if h1 else None

        # Try meta title if no h1
        if not chair_name:
            title_tag = soup.find('title')
            if title_tag:
                chair_name = title_tag.get_text(strip=True).split('|')[0].strip()

        if not chair_name or len(chair_name) < 5:
            return

        # Clean up name (remove "Professur für" prefix in some cases)
        display_name = chair_name

        # Skip if already exists
        chair_uri = create_uri("chair", chair_name)
        if chair_uri in self.chairs:
            return

        # Get description
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')[:500]

        # Determine parent institute from URL path
        parent_uri = None
        url_path = urlparse(url).path

        # Extract institute abbreviation from URL
        # e.g., /institute/lls/professuren/... -> lls
        # e.g., /institute/ipk/philosophie/... -> ipk
        institute_match = re.search(r'/institute/([^/]+)/', url_path)
        if institute_match:
            institute_abbrev = institute_match.group(1).upper()
            # Find matching institute
            for inst_uri, inst in self.organizations.items():
                if inst.org_type == "Institute":
                    if institute_abbrev in inst.name.upper() or institute_abbrev in inst.abbreviation.upper() if inst.abbreviation else False:
                        parent_uri = inst_uri
                        break

        # Find the professor/chair holder
        headed_by_uri = None

        # Look for professor name in page content
        page_text = soup.get_text()

        # Common patterns for finding chair holder
        holder_patterns = [
            r'Leitung[:\s]*([^\n]+)',
            r'Professorship holder[:\s]*([^\n]+)',
            r'Chair holder[:\s]*([^\n]+)',
            r'Lehrstuhlinhaber(?:in)?[:\s]*([^\n]+)',
            r'(Prof\.\s*Dr\.[^,\n<]+)',
        ]

        for pattern in holder_patterns:
            match = re.search(pattern, page_text, re.I)
            if match:
                holder_name = match.group(1).strip()
                holder_name = re.sub(r'\s+', ' ', holder_name)
                holder_name = holder_name.split('\n')[0].strip()[:100]

                if holder_name and len(holder_name) > 5:
                    # Check if this person already exists
                    for person_uri, person in self.persons.items():
                        if holder_name in person.name or person.name in holder_name:
                            headed_by_uri = person_uri
                            break

                    # Create new professor if not found
                    if not headed_by_uri and 'Prof.' in holder_name:
                        first_name, last_name, title = extract_name_parts(holder_name)
                        professor = Person(
                            uri=create_uri("person", holder_name),
                            name=holder_name,
                            first_name=first_name,
                            last_name=last_name,
                            title=title,
                            category="Professor",
                            webpage=url,
                            source_url=url
                        )
                        self.persons[professor.uri] = professor
                        headed_by_uri = professor.uri
                    break

        # Create chair entity
        chair = Chair(
            uri=chair_uri,
            name=chair_name,
            description=description,
            parent=parent_uri,
            headed_by=headed_by_uri,
            webpage=url,
            source_url=url
        )
        self.chairs[chair.uri] = chair

        headed_by_name = "Unknown"
        if headed_by_uri:
            for p in self.persons.values():
                if p.uri == headed_by_uri:
                    headed_by_name = p.name
                    break

        print(f"    Chair: {chair_name[:50]}... (headed by: {headed_by_name})")

    def scrape_hiwi_positions(self):
        """Scrape Student Assistant (Hiwi) position postings.
        
        This answers the competency question: "What Hiwi positions are currently available?"
        """
        print("\n=== Scraping Hiwi Positions ===")
        
        url = SEED_URLS.get("hiwi_positions")
        if not url:
            print("No Hiwi positions URL configured")
            return
        
        soup = self.get_soup(url)
        if not soup:
            return
        
        self.visited_urls.add(url)
        
        # Find all position links on the assistants page
        position_links = []
        
        # Look for links to individual position pages
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            text = link.get_text(strip=True)

            # Position pages follow pattern: /hilfskraefte/hilfskraefte-ansicht/YYYY/MM/DD/...
            # or English: /assistants/assistants-singleview/YYYY/MM/DD/...
            if ('/hilfskraefte/hilfskraefte-ansicht/' in href or
                '/assistants/assistants-singleview/' in href or
                ('/hilfskraefte/' in href and href.endswith('.html') and 'hilfskraefte.html' not in href)):
                full_url = urljoin(BASE_URL, href)
                if full_url not in self.visited_urls and text:
                    position_links.append((text, full_url))
        
        print(f"  Found {len(position_links)} Hiwi position postings")
        
        # Scrape each position page
        for position_title, position_url in position_links:
            self._scrape_single_hiwi_position(position_title, position_url)
            time.sleep(0.5)
    
    def _scrape_single_hiwi_position(self, title: str, url: str):
        """Scrape a single Hiwi position posting page."""
        soup = self.get_soup(url)
        if not soup:
            return
        
        self.visited_urls.add(url)
        
        # Get better title from page if available
        h1 = soup.find('h1')
        if h1:
            title = h1.get_text(strip=True)
        
        if not title or len(title) < 5:
            return
        
        # Skip if already exists
        position_uri = create_uri("hiwi-position", title)
        if position_uri in self.hiwi_positions:
            return
        
        # Get description
        description = None
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            description = meta_desc.get('content', '')[:1000]
        
        # Try to find description in page content
        if not description:
            content_div = soup.find('div', class_=re.compile(r'content|article|main', re.I))
            if content_div:
                paragraphs = content_div.find_all('p')
                if paragraphs:
                    description = ' '.join([p.get_text(strip=True) for p in paragraphs[:3]])[:1000]
        
        # Extract contact person
        contact_person = None
        contact_email = None
        
        # Look for contact information
        page_text = soup.get_text()
        
        # Find email
        email_match = re.search(r'[\w\.-]+@leuphana\.de', page_text)
        if email_match:
            contact_email = email_match.group()
        
        # Look for hours per week
        hours_per_week = None
        hours_match = re.search(r'(\d+)\s*(Stunden|hours|h)\s*(/|per)?\s*(Woche|week|w)?', page_text, re.I)
        if hours_match:
            hours_per_week = f"{hours_match.group(1)} hours/week"
        
        # Extract posted date from URL (format: YYYY/MM/DD)
        posted_date = None
        date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
        if date_match:
            posted_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        
        # Try to identify department/institute
        department = None
        for inst_uri, inst in self.organizations.items():
            if inst.org_type == "Institute":
                if inst.name.lower() in page_text.lower() or (inst.abbreviation and inst.abbreviation.lower() in page_text.lower()):
                    department = inst.name
                    break
        
        # Create position entity
        position = HiwiPosition(
            uri=position_uri,
            title=title,
            description=description,
            department=department,
            contact_email=contact_email,
            posted_date=posted_date,
            hours_per_week=hours_per_week,
            webpage=url,
            source_url=url
        )
        self.hiwi_positions[position.uri] = position
        
        print(f"    Created Hiwi position: {title[:50]}...")
        if department:
            print(f"      Department: {department}")

    def scrape_study_programs(self):
        """Scrape study programs from College, Graduate School, and Professional School."""
        print("\n=== Scraping Study Programs ===")

        if "programs" not in SEED_URLS:
            print("No program URLs configured")
            return

        program_type_mapping = {
            "bachelor": ("BachelorProgram", "College"),
            "master": ("MasterProgram", "Graduate School"),
            "professional": ("MasterProgram", "Professional School"),
        }

        for prog_key, url in SEED_URLS["programs"].items():
            prog_type, offered_by = program_type_mapping.get(prog_key, ("StudyProgram", "Leuphana"))
            print(f"Scraping {prog_key} programs from {url}")

            soup = self.get_soup(url)
            if not soup:
                continue

            # Find program links - look for common patterns
            program_links = []

            # Pattern 1: Links containing program-related keywords
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)

                # Skip navigation, footer, etc.
                if len(text) < 5 or len(text) > 100:
                    continue
                if any(skip in text.lower() for skip in ['more', 'read', 'contact', 'apply', 'login', 'menu']):
                    continue

                # Check if it looks like a program link
                if '/college/' in href or '/graduate-school/' in href or '/professional-school/' in href:
                    if 'programme' in href or 'program' in href or 'studies' in href or 'major' in href:
                        full_url = urljoin(BASE_URL, href)
                        if full_url not in self.visited_urls:
                            program_links.append((text, full_url))

            # Pattern 2: Look for program listings in specific sections
            for section in soup.find_all(['div', 'ul', 'section'], class_=re.compile(r'program|course|study|major', re.I)):
                for link in section.find_all('a', href=True):
                    text = link.get_text(strip=True)
                    href = link.get('href', '')
                    if text and len(text) > 5 and href:
                        full_url = urljoin(BASE_URL, href)
                        if full_url not in self.visited_urls and (text, full_url) not in program_links:
                            program_links.append((text, full_url))

            print(f"  Found {len(program_links)} potential programs")

            # Create program entities
            for prog_name, prog_url in program_links[:30]:  # Limit to 30 per category
                # Skip if already exists
                if any(p.name == prog_name for p in self.programs.values()):
                    continue

                # Fetch program page for details
                prog_soup = self.get_soup(prog_url)
                description = None
                duration = None
                language = None

                if prog_soup:
                    self.visited_urls.add(prog_url)

                    # Get description from meta or first paragraph
                    meta_desc = prog_soup.find('meta', attrs={'name': 'description'})
                    if meta_desc:
                        description = meta_desc.get('content', '')[:500]

                    # Look for duration info
                    for text_node in prog_soup.find_all(string=re.compile(r'semester|year|duration', re.I)):
                        parent = text_node.parent
                        if parent:
                            duration_text = parent.get_text(strip=True)
                            duration_match = re.search(r'(\d+)\s*semester', duration_text, re.I)
                            if duration_match:
                                duration = f"{duration_match.group(1)} semesters"
                                break

                    # Look for language info
                    for text_node in prog_soup.find_all(string=re.compile(r'english|german|language', re.I)):
                        parent = text_node.parent
                        if parent:
                            lang_text = parent.get_text(strip=True).lower()
                            if 'english' in lang_text:
                                language = "English"
                            elif 'german' in lang_text:
                                language = "German"
                            break

                program = StudyProgram(
                    uri=create_uri("program", prog_name),
                    name=prog_name,
                    program_type=prog_type,
                    description=description,
                    duration=duration,
                    language=language,
                    offered_by=create_uri("school", offered_by),
                    webpage=prog_url,
                    source_url=url
                )
                self.programs[program.uri] = program

                time.sleep(0.3)  # Be polite

            time.sleep(REQUEST_CONFIG["request_delay"])
    
    # =========================================================================
    # Sitemap-Based Extraction Methods
    # =========================================================================

    def load_sitemap_urls(self, sitemap_file: str) -> List[str]:
        """Parse sitemap and return all URLs.

        Args:
            sitemap_file: Path to sitemapurls.txt

        Returns:
            List of all URLs from sitemap
        """
        urls = []

        try:
            with open(sitemap_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('TYPO3') or line.startswith('This XML') or line.startswith('URL'):
                        continue
                    url = line.split('\t')[0].strip()
                    if url and url.startswith('http'):
                        urls.append(url)
        except FileNotFoundError:
            print(f"Sitemap file not found: {sitemap_file}")

        return urls

    def categorize_sitemap_urls(self, sitemap_file: str) -> Dict[str, List[str]]:
        """Parse sitemap and categorize URLs by entity type.

        Args:
            sitemap_file: Path to sitemapurls.txt

        Returns:
            Dict with keys: 'persons', 'minors', 'research_centers', 'research_projects', 'bachelor_programs'
        """
        categorized = {
            'persons': [],
            'minors': [],
            'research_centers': [],
            'research_projects': [],
            'bachelor_programs': [],
        }

        try:
            with open(sitemap_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Skip header lines
                    if line.startswith('TYPO3') or line.startswith('This XML') or line.startswith('URL'):
                        continue

                    url = line.split('\t')[0].strip()
                    if not url or not url.startswith('http'):
                        continue

                    # Categorize by URL pattern
                    # Person profiles (skip list pages like /personen.html)
                    if '/personen/' in url and url.endswith('.html'):
                        if not url.endswith('/personen.html') and not url.endswith('/personen/ehemalige.html'):
                            # Skip special pages that aren't individual profiles
                            if not any(x in url for x in ['lehrbeauftragte', 'einzelseiten', 'professorinnen', 'stipendiatinnen']):
                                categorized['persons'].append(url)

                    # Minor programs
                    elif re.match(MINOR_URL_PATTERN, url):
                        categorized['minors'].append(url)

                    # Research centers (main pages only, not subpages)
                    elif re.match(RESEARCH_CENTER_URL_PATTERN, url):
                        categorized['research_centers'].append(url)

                    # Research projects
                    elif any(re.search(pattern, url) for pattern in RESEARCH_PROJECT_PATTERNS):
                        categorized['research_projects'].append(url)

                    # Bachelor programs (excluding minors)
                    elif re.match(BACHELOR_PROGRAM_PATTERN, url) and 'minor-' not in url:
                        categorized['bachelor_programs'].append(url)

        except FileNotFoundError:
            print(f"Sitemap file not found: {sitemap_file}")

        return categorized

    def scrape_all_persons_from_sitemap(self, sitemap_file: str, max_persons: int = None):
        """Extract all person profiles from sitemap systematically.

        Args:
            sitemap_file: Path to sitemapurls.txt
            max_persons: Optional limit for testing
        """
        print("\n=== Scraping Person Profiles from Sitemap ===")

        urls = self.categorize_sitemap_urls(sitemap_file)
        person_urls = urls['persons']

        print(f"Found {len(person_urls)} person URLs in sitemap")

        if max_persons:
            person_urls = person_urls[:max_persons]
            print(f"Limited to {max_persons} persons for testing")

        for i, url in enumerate(tqdm(person_urls, desc="Extracting persons")):
            if url in self.visited_urls:
                continue

            soup = self.get_soup(url)
            if not soup:
                continue

            self.visited_urls.add(url)

            # Extract name from h1 or page title
            name = None
            h1 = soup.find('h1')
            if h1:
                name = h1.get_text(strip=True)

            if not name or len(name) < 2:
                # Try meta title
                title_tag = soup.find('title')
                if title_tag:
                    name = title_tag.get_text(strip=True).split('|')[0].strip()

            if not name or len(name) < 2:
                continue

            # Skip non-person pages (page sections, topic pages, etc.)
            non_person_patterns = [
                'reden und vorträge', 'speeches', 'vorträge', 'lectures',
                'publikationen', 'publications', 'projekte', 'projects',
                'forschung', 'research', 'lehre', 'teaching', 'vita', 'cv',
                'kontakt', 'contact', 'team', 'mitarbeiter', 'staff',
                'impressum', 'imprint', 'datenschutz', 'privacy'
            ]
            name_lower = name.lower()
            if any(pattern in name_lower for pattern in non_person_patterns):
                continue

            # Skip if name doesn't look like a person's name (no first/last name pattern)
            # Persons typically have at least 2 capitalized words
            name_words = [w for w in name.split() if w[0:1].isupper() and len(w) > 1]
            if len(name_words) < 2 and 'Prof.' not in name and 'Dr.' not in name:
                continue

            # Extract name parts and title
            first_name, last_name, title = extract_name_parts(name)

            # Extract contact info
            email = extract_email(soup)
            phone = extract_phone(soup)

            # Extract office/room
            office = None
            for selector in SELECTORS["person"]["office"]:
                elem = soup.select_one(selector)
                if elem:
                    office = elem.get_text(strip=True)
                    break

            # Determine institute from URL or page content
            institute = None

            # Method 1: Extract from URL path
            institute_match = re.search(r'/institute[s]?/([^/]+)/', url)
            if institute_match:
                institute = institute_match.group(1).upper()
            else:
                center_match = re.search(r'/zentren/([^/]+)/', url)
                if center_match:
                    institute = center_match.group(1).upper()

            # Method 2: Extract from page content if not found in URL
            if not institute:
                full_page_text = soup.get_text()
                # Look for institute patterns in page
                institute_patterns = [
                    r'Institut für\s+([^,\n\|]+)',
                    r'Institute of\s+([^,\n\|]+)',
                    r'\b(I[A-Z]{2,5})\b',  # Abbreviations like IBIWI, IES
                    r'Centre for\s+([^,\n\|]+)',
                    r'Zentrum für\s+([^,\n\|]+)',
                ]
                for pattern in institute_patterns:
                    match = re.search(pattern, full_page_text, re.I)
                    if match:
                        institute = match.group(1).strip()[:50]
                        break

            # Method 3: Try to link based on breadcrumb or navigation
            if not institute:
                breadcrumb = soup.find(['nav', 'ol', 'ul'], class_=re.compile(r'breadcrumb', re.I))
                if breadcrumb:
                    crumb_text = breadcrumb.get_text()
                    if 'Institute' in crumb_text or 'Institut' in crumb_text:
                        inst_match = re.search(r'Institut[e]?\s+(?:für|of)\s+([^»\n]+)', crumb_text)
                        if inst_match:
                            institute = inst_match.group(1).strip()[:50]

            # Get page text for category detection
            page_text = soup.get_text()[:2000]

            # Determine category
            category = determine_person_category(page_text, url, title or "")

            # Create Person entity
            person = Person(
                uri=create_uri("person", name),
                name=name,
                first_name=first_name,
                last_name=last_name,
                title=title,
                category=category,
                email=email,
                phone=phone,
                office=office,
                webpage=url,
                institute=institute,
                source_url=url
            )

            self.persons[person.uri] = person

            # Rate limiting
            if i % 10 == 0:
                time.sleep(REQUEST_CONFIG["request_delay"])
            else:
                time.sleep(0.3)

        print(f"Extracted {len(self.persons)} persons total")

    def scrape_minor_programs(self, sitemap_file: str):
        """Extract all Minor programs from sitemap.

        Found 23 minor programs with pattern: /college/bachelor/minor-{name}.html
        """
        print("\n=== Scraping Minor Programs ===")

        urls = self.categorize_sitemap_urls(sitemap_file)
        minor_urls = urls['minors']

        print(f"Found {len(minor_urls)} minor program URLs")

        for url in tqdm(minor_urls, desc="Extracting minors"):
            if url in self.visited_urls:
                continue

            soup = self.get_soup(url)
            if not soup:
                continue

            self.visited_urls.add(url)

            # Extract name from h1 or page title
            name = None
            h1 = soup.find('h1')
            if h1:
                name = h1.get_text(strip=True)

            if not name:
                # Extract from URL: minor-betriebswirtschaftslehre -> Betriebswirtschaftslehre
                name_from_url = re.search(r'minor-([^.]+)\.html', url)
                if name_from_url:
                    name = name_from_url.group(1).replace('-', ' ').title()

            if not name:
                continue

            # German name (original page is German)
            name_de = name

            # Extract description
            description = None
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta:
                description = meta.get('content', '')[:500]

            # Also try teaser text
            if not description:
                teaser = soup.select_one('.teaser, .intro, .lead')
                if teaser:
                    description = teaser.get_text(strip=True)[:500]

            minor = Minor(
                uri=create_uri("minor", name),
                name=name,
                name_de=name_de,
                description=description,
                offered_by="http://leuphana.de/resource/school/college",
                webpage=url,
                source_url=url
            )

            self.minors[minor.uri] = minor
            time.sleep(0.3)

        print(f"Extracted {len(self.minors)} minors")

    def scrape_research_centers(self, sitemap_file: str):
        """Extract Research Centers (Zentren) from sitemap.

        Research centers are found at: /zentren/{name}.html
        """
        print("\n=== Scraping Research Centers ===")

        urls = self.categorize_sitemap_urls(sitemap_file)
        center_urls = urls['research_centers']

        print(f"Found {len(center_urls)} research center URLs")

        for url in tqdm(center_urls, desc="Extracting research centers"):
            if url in self.visited_urls:
                continue

            soup = self.get_soup(url)
            if not soup:
                continue

            self.visited_urls.add(url)

            # Extract center name
            h1 = soup.find('h1')
            name = h1.get_text(strip=True) if h1 else None

            if not name:
                # Extract from URL
                name_match = re.search(r'/zentren/([^/]+)\.html', url)
                if name_match:
                    name = name_match.group(1).replace('-', ' ').title()

            if not name:
                continue

            # Extract abbreviation if present (e.g., "ZAG" from "Center for Applied... (ZAG)")
            abbrev_match = re.search(r'\(([A-Z]{2,})\)', name)
            abbreviation = abbrev_match.group(1) if abbrev_match else None

            # If no abbreviation found, try from URL
            if not abbreviation:
                url_abbrev = re.search(r'/zentren/([a-z]+)\.html', url)
                if url_abbrev:
                    abbreviation = url_abbrev.group(1).upper()

            # Extract description
            description = None
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta:
                description = meta.get('content', '')[:500]

            if not description:
                teaser = soup.select_one('.teaser, .intro, .lead, .description')
                if teaser:
                    description = teaser.get_text(strip=True)[:500]

            center = Organization(
                uri=create_uri("research-center", name),
                name=name,
                org_type="ResearchCenter",
                abbreviation=abbreviation,
                description=description,
                parent="http://leuphana.de/resource/university/leuphana",
                webpage=url,
                source_url=url
            )

            self.organizations[center.uri] = center
            time.sleep(REQUEST_CONFIG["request_delay"])

        print(f"Extracted research centers, total organizations: {len(self.organizations)}")

    def scrape_research_projects(self, sitemap_file: str):
        """Extract Research Projects from sitemap.

        Found project pages with patterns:
        - /forschung-projekte/
        - /drittmittelprojekte/
        """
        print("\n=== Scraping Research Projects ===")

        urls = self.categorize_sitemap_urls(sitemap_file)
        project_urls = urls['research_projects']

        print(f"Found {len(project_urls)} research project URLs")

        for url in tqdm(project_urls, desc="Extracting projects"):
            if url in self.visited_urls:
                continue

            # Skip index/listing pages
            if url.endswith('/forschung-projekte.html') or url.endswith('/projekte.html'):
                continue

            soup = self.get_soup(url)
            if not soup:
                continue

            self.visited_urls.add(url)

            h1 = soup.find('h1')
            name = h1.get_text(strip=True) if h1 else None

            if not name or len(name) < 5:
                continue

            # Extract description
            description = None
            meta = soup.find('meta', attrs={'name': 'description'})
            if meta:
                description = meta.get('content', '')[:1000]

            if not description:
                teaser = soup.select_one('.teaser, .intro, .lead, .description')
                if teaser:
                    description = teaser.get_text(strip=True)[:1000]

            # Identify conducting organization from URL
            conducted_by = None
            if '/institute/' in url:
                inst_match = re.search(r'/institute/([^/]+)/', url)
                if inst_match:
                    conducted_by = create_uri("institute", inst_match.group(1))
            elif '/zentren/' in url:
                center_match = re.search(r'/zentren/([^/]+)/', url)
                if center_match:
                    conducted_by = create_uri("research-center", center_match.group(1))

            # Look for funding information
            page_text = soup.get_text()
            funding_source = None
            funding_patterns = ['DFG', 'BMBF', 'EU', 'Horizon', 'VolkswagenStiftung', 'DAAD']
            for funder in funding_patterns:
                if funder.lower() in page_text.lower():
                    funding_source = funder
                    break

            project = ResearchProject(
                uri=create_uri("project", name),
                name=name,
                description=description,
                conducted_by=conducted_by,
                funding_source=funding_source,
                webpage=url,
                source_url=url
            )

            self.research_projects[project.uri] = project
            time.sleep(0.3)

        print(f"Extracted {len(self.research_projects)} research projects")

    def scrape_bachelor_programs_from_sitemap(self, sitemap_file: str):
        """Extract bachelor programs from sitemap.

        Args:
            sitemap_file: Path to sitemapurls.txt

        This extracts actual bachelor programs (not minors, which are handled separately).
        URLs follow pattern: /college/bachelor/{program-name}.html
        """
        print("\n=== Scraping Bachelor Programs from Sitemap ===")

        urls = self.categorize_sitemap_urls(sitemap_file)
        bachelor_urls = urls['bachelor_programs']

        print(f"Found {len(bachelor_urls)} bachelor program URLs")

        for url in tqdm(bachelor_urls, desc="Extracting bachelor programs"):
            if url in self.visited_urls:
                continue

            soup = self.get_soup(url)
            if not soup:
                continue

            self.visited_urls.add(url)

            # Extract name from h1 or page title
            name = None
            h1 = soup.find('h1')
            if h1:
                name = h1.get_text(strip=True)

            if not name:
                # Extract from URL: kulturwissenschaften -> Kulturwissenschaften
                name_from_url = re.search(r'/college/bachelor/([^.]+)\.html', url)
                if name_from_url:
                    name = name_from_url.group(1).replace('-', ' ').title()

            if not name or len(name) < 2:
                continue

            # Skip if already exists
            program_uri = create_uri("program", name)
            if program_uri in self.programs:
                continue

            # Get description
            description = None
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc:
                description = meta_desc.get('content', '')[:500]

            # Look for duration info
            duration = None
            page_text = soup.get_text()
            duration_match = re.search(r'(\d+)\s*semester', page_text, re.I)
            if duration_match:
                duration = f"{duration_match.group(1)} semesters"

            # Look for language info
            language = None
            if 'english' in page_text.lower():
                language = "English"
            elif 'german' in page_text.lower() or 'deutsch' in page_text.lower():
                language = "German"

            program = StudyProgram(
                uri=program_uri,
                name=name,
                program_type="BachelorProgram",
                description=description,
                duration=duration,
                language=language,
                offered_by=create_uri("school", "College"),
                webpage=url,
                source_url=url
            )

            self.programs[program.uri] = program
            time.sleep(0.3)

        print(f"Total bachelor programs: {len([p for p in self.programs.values() if p.program_type == 'BachelorProgram'])}")

    def scrape_courses(self):
        """Scrape courses from the Vorlesungsverzeichnis (course catalog).

        This extracts courses and creates the critical relationships:
        - Professor -> teaches -> Course
        - Course -> partOf -> Program

        The Vorlesungsverzeichnis uses a query-parameter system:
        - ?mode=gebietsliste&studiengang_id=X - list areas for a program
        - ?mode=modulliste&gebiet_id=X - list modules in an area
        - ?mode=veranstaltungsliste&modul_id=X&gebiet_id=Y - list courses
        """
        print("\n=== Scraping Courses from Vorlesungsverzeichnis ===")

        base_url = "https://www.leuphana.de/services/vorlesungsverzeichnis.html"

        # First, get all study program IDs from the main page
        soup = self.get_soup(base_url)
        if not soup:
            return

        # Find all program links with studiengang_id parameter
        program_ids = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            match = re.search(r'studiengang_id=(\d+)', href)
            if match:
                program_ids.add(match.group(1))

        print(f"  Found {len(program_ids)} study programs in Vorlesungsverzeichnis")

        # Limit to a representative sample for efficiency
        program_ids = list(program_ids)[:30]

        # For each program, get areas, then modules, then courses
        for prog_id in tqdm(program_ids, desc="Scraping programs for courses"):
            self._scrape_program_courses(base_url, prog_id)
            time.sleep(0.3)

        print(f"Total courses extracted: {len(self.courses)}")
        courses_with_instructor = len([c for c in self.courses.values() if c.taught_by])
        print(f"Courses with instructor: {courses_with_instructor}")

    def _scrape_program_courses(self, base_url: str, program_id: str):
        """Scrape courses for a specific program via the Vorlesungsverzeichnis."""
        # Get areas (Gebiete) for this program
        areas_url = f"{base_url}?mode=gebietsliste&studiengang_id={program_id}"
        soup = self.get_soup(areas_url)
        if not soup:
            return

        # Find area IDs
        area_ids = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            match = re.search(r'gebiet_id=(\d+)', href)
            if match:
                area_ids.add(match.group(1))

        # Get program name for linking
        program_name = None
        h1 = soup.find('h1')
        if h1:
            program_name = h1.get_text(strip=True)

        # Find matching program URI - try multiple matching strategies
        program_uri = None
        if program_name:
            program_name_lower = program_name.lower()
            # Strategy 1: Exact or substring match
            for p_uri, p in self.programs.items():
                p_name_lower = p.name.lower()
                if program_name_lower in p_name_lower or p_name_lower in program_name_lower:
                    program_uri = p_uri
                    break

            # Strategy 2: Word-based matching (at least 2 significant words match)
            if not program_uri:
                program_words = set(w for w in re.findall(r'\b\w{4,}\b', program_name_lower)
                                   if w not in {'studiengang', 'program', 'study', 'bachelor', 'master'})
                for p_uri, p in self.programs.items():
                    p_words = set(w for w in re.findall(r'\b\w{4,}\b', p.name.lower())
                                 if w not in {'studiengang', 'program', 'study', 'bachelor', 'master'})
                    if len(program_words & p_words) >= 2:
                        program_uri = p_uri
                        break

            # Strategy 3: Create a reference to College/Graduate School based on program type
            if not program_uri:
                if 'bachelor' in program_name_lower or 'b.a.' in program_name_lower or 'b.sc.' in program_name_lower:
                    program_uri = create_uri("school", "College")
                elif 'master' in program_name_lower or 'm.a.' in program_name_lower or 'm.sc.' in program_name_lower:
                    program_uri = create_uri("school", "Graduate School")

        # For each area, get modules and courses
        for area_id in list(area_ids)[:10]:  # Limit per program
            self._scrape_area_courses(base_url, area_id, program_uri)

    def _scrape_area_courses(self, base_url: str, area_id: str, program_uri: str):
        """Scrape courses for a specific area/module."""
        # Get modules for this area
        modules_url = f"{base_url}?mode=modulliste&gebiet_id={area_id}"
        soup = self.get_soup(modules_url)
        if not soup:
            return

        # Find module IDs
        module_ids = set()
        for link in soup.find_all('a', href=True):
            href = link.get('href', '')
            match = re.search(r'modul_id=(\d+)', href)
            if match:
                module_ids.add((match.group(1), area_id))

        # For each module, get courses
        for modul_id, geb_id in list(module_ids)[:5]:  # Limit per area
            self._scrape_module_courses(base_url, modul_id, geb_id, program_uri)

    def _scrape_module_courses(self, base_url: str, modul_id: str, gebiet_id: str, program_uri: str):
        """Scrape individual courses from a module listing."""
        courses_url = f"{base_url}?mode=veranstaltungsliste&modul_id={modul_id}&gebiet_id={gebiet_id}"
        soup = self.get_soup(courses_url)
        if not soup:
            return

        # Field labels to skip - these are NOT course names
        skip_labels = {
            'dozent/in', 'dozent', 'dozentin', 'termin', 'inhalt', 'raum', 'room',
            'zeit', 'time', 'ort', 'place', 'credits', 'ects', 'cp', 'beschreibung',
            'description', 'bemerkung', 'note', 'literatur', 'literature',
            'anmeldung', 'registration', 'prüfung', 'exam', 'modul', 'module',
            'leuphana bachelor', 'leuphana semester', 'sozialpädagogik',
            'wirtschaftspädagogik', 'lehrerbildung', 'studiengang'
        }

        # Course type indicators - real courses usually have these
        course_type_indicators = ['(seminar)', '(vorlesung)', '(übung)', '(praktikum)',
                                   '(projekt)', '(kolloquium)', '(tutorium)', '(lecture)',
                                   '(tutorial)', '(workshop)', 'seminar', 'vorlesung']

        # Find instructor links - pattern: Dozent/in: <a href="...personinfo...">Name</a>
        instructor_links = {}
        for text_node in soup.find_all(string=re.compile(r'Dozent', re.I)):
            parent = text_node.parent
            if parent:
                # Look for nearby link with personinfo
                link = parent.find('a', href=re.compile(r'personinfo|person_id'))
                if link:
                    instructor_name = link.get_text(strip=True)
                    # Map this instructor to nearby course heading
                    instructor_links[parent] = instructor_name

        # Find actual course titles - they typically end with course type in parentheses
        for elem in soup.find_all(['h2', 'h3', 'h4', 'strong']):
            course_name = elem.get_text(strip=True)

            # Skip if too short or too long
            if len(course_name) < 8 or len(course_name) > 200:
                continue

            # Skip known field labels
            name_lower = course_name.lower().strip()
            if any(name_lower == skip or name_lower.startswith(skip + ':') or name_lower.endswith(':')
                   for skip in skip_labels):
                continue

            # Skip if it's just a label ending with colon
            if name_lower.endswith(':'):
                continue

            # Skip navigation/generic items
            if any(skip in name_lower for skip in ['suche', 'search', 'home', 'menu', 'navigation', 'zurück', 'back']):
                continue

            # Prefer courses with type indicators, but allow others with sufficient length
            has_type_indicator = any(ind in name_lower for ind in course_type_indicators)

            # If no type indicator, require longer name and check it's not a program name
            if not has_type_indicator:
                if len(course_name) < 20:
                    continue
                # Skip if it looks like a degree program name
                if any(prog in name_lower for prog in ['bachelor', 'master', 'b.a.', 'm.a.', 'b.sc.', 'm.sc.']):
                    continue

            # Find instructor for this course
            instructor_name = None

            # Method 1: Look for Dozent/in pattern after this heading
            next_siblings = elem.find_all_next(limit=10)
            for sibling in next_siblings:
                sibling_text = sibling.get_text() if sibling else ''
                if 'Dozent' in sibling_text:
                    # Find the instructor link
                    link = sibling.find('a', href=re.compile(r'personinfo|person_id'))
                    if link:
                        instructor_name = link.get_text(strip=True)
                        break
                    # Or extract name from text
                    dozent_match = re.search(r'Dozent[/\w]*:\s*(.+?)(?:\n|$)', sibling_text)
                    if dozent_match:
                        instructor_name = dozent_match.group(1).strip()[:80]
                        break
                # Stop if we hit another course heading
                if sibling.name in ['h2', 'h3', 'h4'] and sibling != elem:
                    break

            # Determine course type from name
            course_type = None
            if '(vorlesung' in name_lower or 'vorlesung)' in name_lower:
                course_type = "Lecture"
            elif '(seminar' in name_lower or 'seminar)' in name_lower:
                course_type = "Seminar"
            elif '(übung' in name_lower or 'übung)' in name_lower:
                course_type = "Tutorial"
            elif '(praktikum' in name_lower or 'praktikum)' in name_lower:
                course_type = "Practical"
            elif '(projekt' in name_lower or 'projekt)' in name_lower:
                course_type = "Project"
            elif '(kolloquium' in name_lower:
                course_type = "Colloquium"
            elif '(tutorium' in name_lower:
                course_type = "Tutorial"

            self._create_course_entity(
                name=course_name,
                instructor_name=instructor_name,
                credits=None,
                program_uri=program_uri,
                course_type=course_type,
                source_url=courses_url
            )

    def _scrape_course_listing_page(self, section_name: str, url: str):
        """Scrape a course listing page for individual courses."""
        soup = self.get_soup(url)
        if not soup:
            return

        self.visited_urls.add(url)

        # Try to determine which program this belongs to
        program_uri = None
        page_text = soup.get_text().lower()

        # Map page content to programs
        program_keywords = {
            'bachelor': None,  # Will try to find specific bachelor program
            'master': None,
            'college': create_uri("school", "College"),
            'graduate school': create_uri("school", "Graduate School"),
        }

        for keyword, prog_uri in program_keywords.items():
            if keyword in page_text:
                program_uri = prog_uri
                break

        # Look for course/module entries
        # Common patterns: tables, lists with course info
        course_entries = []

        # Pattern 1: Tables with course information
        for table in soup.find_all('table'):
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    course_name = cells[0].get_text(strip=True)
                    if course_name and len(course_name) > 5 and len(course_name) < 200:
                        # Try to get instructor from another cell
                        instructor = None
                        credits = None
                        for cell in cells[1:]:
                            cell_text = cell.get_text(strip=True)
                            # Check if it's credits (ECTS/CP)
                            credit_match = re.search(r'(\d+)\s*(?:CP|ECTS|LP)', cell_text, re.I)
                            if credit_match:
                                credits = int(credit_match.group(1))
                            # Check if it looks like a name (has Prof., Dr., or capitalized)
                            if 'Prof.' in cell_text or 'Dr.' in cell_text:
                                instructor = cell_text

                        course_entries.append({
                            'name': course_name,
                            'instructor': instructor,
                            'credits': credits,
                        })

        # Pattern 2: Headings followed by instructor info
        for heading in soup.find_all(['h2', 'h3', 'h4']):
            heading_text = heading.get_text(strip=True)
            if len(heading_text) > 5 and len(heading_text) < 200:
                # Check following elements for instructor info
                next_elem = heading.find_next_sibling()
                instructor = None
                if next_elem:
                    next_text = next_elem.get_text(strip=True)
                    if 'Prof.' in next_text or 'Dr.' in next_text:
                        instructor = next_text.split('\n')[0][:100]

                course_entries.append({
                    'name': heading_text,
                    'instructor': instructor,
                    'credits': None,
                })

        # Create course entities
        for entry in course_entries:
            self._create_course_entity(
                name=entry['name'],
                instructor_name=entry.get('instructor'),
                credits=entry.get('credits'),
                program_uri=program_uri,
                source_url=url
            )

    def _extract_courses_from_program_page(self, program: StudyProgram):
        """Extract course information embedded in program pages."""
        if not program.webpage or program.webpage in self.visited_urls:
            return

        soup = self.get_soup(program.webpage)
        if not soup:
            return

        # Don't re-visit but don't mark as visited (might be needed elsewhere)
        page_text = soup.get_text()

        # Look for module/course sections
        module_sections = soup.find_all(['div', 'section'], class_=re.compile(r'module|course|curriculum|studienplan', re.I))

        for section in module_sections:
            # Find course names in this section
            for item in section.find_all(['li', 'p', 'h3', 'h4']):
                text = item.get_text(strip=True)
                # Skip if too short or too long
                if len(text) < 5 or len(text) > 200:
                    continue
                # Skip if it looks like navigation
                if any(skip in text.lower() for skip in ['read more', 'contact', 'apply', 'login']):
                    continue

                # Check if this looks like a course name (contains common patterns)
                if any(keyword in text.lower() for keyword in ['module', 'seminar', 'lecture', 'vorlesung', 'übung', 'praktikum']):
                    self._create_course_entity(
                        name=text,
                        instructor_name=None,
                        credits=None,
                        program_uri=program.uri,
                        source_url=program.webpage
                    )

    def _create_course_entity(self, name: str, instructor_name: str = None,
                              credits: int = None, program_uri: str = None,
                              course_type: str = None, source_url: str = ""):
        """Create a Course entity with relationships."""
        # Clean up name
        name = name.strip()
        if not name or len(name) < 3:
            return

        # Skip duplicates
        course_uri = create_uri("course", name)
        if course_uri in self.courses:
            return

        # Find instructor person if provided
        taught_by = []
        if instructor_name:
            instructor_name = instructor_name.strip()
            # Look for existing person
            for person_uri, person in self.persons.items():
                if instructor_name in person.name or person.name in instructor_name:
                    taught_by.append(person_uri)
                    break

            # If not found and looks like a professor, create new person
            if not taught_by and ('Prof.' in instructor_name or 'Dr.' in instructor_name):
                first_name, last_name, title = extract_name_parts(instructor_name)
                new_person = Person(
                    uri=create_uri("person", instructor_name),
                    name=instructor_name,
                    first_name=first_name,
                    last_name=last_name,
                    title=title,
                    category="Professor" if "Prof." in instructor_name else "Lecturer",
                    source_url=source_url
                )
                self.persons[new_person.uri] = new_person
                taught_by.append(new_person.uri)

        # Determine course type from name if not provided
        if not course_type:
            name_lower = name.lower()
            if 'seminar' in name_lower:
                course_type = "Seminar"
            elif 'vorlesung' in name_lower or 'lecture' in name_lower:
                course_type = "Lecture"
            elif 'übung' in name_lower or 'tutorial' in name_lower:
                course_type = "Tutorial"
            elif 'praktikum' in name_lower or 'lab' in name_lower:
                course_type = "Practical"
            elif 'projekt' in name_lower or 'project' in name_lower:
                course_type = "Project"

        course = Course(
            uri=course_uri,
            name=name,
            credit_points=credits,
            course_type=course_type,
            part_of_program=program_uri,
            taught_by=taught_by,
            source_url=source_url
        )

        self.courses[course.uri] = course

    def create_university_entity(self):
        """Create the main university entity."""
        university = Organization(
            uri="http://leuphana.de/resource/university/leuphana",
            name="Leuphana University of Lüneburg",
            org_type="University",
            abbreviation="Leuphana",
            description="Leuphana University of Lüneburg is a public university in Lüneburg, Lower Saxony, Germany.",
            webpage=BASE_URL_EN,
            address="Universitätsallee 1, 21335 Lüneburg, Germany",
            source_url=BASE_URL_EN
        )
        self.organizations[university.uri] = university
    
    def run(self, sitemap_file: str = None):
        """Run the complete scraping pipeline.

        Args:
            sitemap_file: Optional path to sitemapurls.txt for comprehensive extraction
        """
        print("=" * 60)
        print("Leuphana University Knowledge Graph - Web Scraper")
        print("=" * 60)

        start_time = time.time()

        # Create main university entity
        self.create_university_entity()

        # Scrape schools and institutes
        self.scrape_all_schools()

        # Scrape staff from directories
        self.scrape_staff_directories()

        # Scrape professorships (chairs)
        self.scrape_professorships()

        # NEW: Comprehensive person extraction from sitemap
        if sitemap_file:
            self.scrape_all_persons_from_sitemap(sitemap_file)

        # NEW: Minor programs
        if sitemap_file:
            self.scrape_minor_programs(sitemap_file)

        # NEW: Research centers
        if sitemap_file:
            self.scrape_research_centers(sitemap_file)

        # NEW: Research projects
        if sitemap_file:
            self.scrape_research_projects(sitemap_file)

        # NEW: Chairs from sitemap
        if sitemap_file:
            sitemap_urls = self.load_sitemap_urls(sitemap_file)
            self.scrape_chairs_from_sitemap(sitemap_urls)

        # Scrape Hiwi positions
        self.scrape_hiwi_positions()

        # Scrape study programs
        self.scrape_study_programs()

        # NEW: Bachelor programs from sitemap (comprehensive)
        if sitemap_file:
            self.scrape_bachelor_programs_from_sitemap(sitemap_file)

        # NEW: Courses from Vorlesungsverzeichnis
        self.scrape_courses()

        # Save results
        self.save_results()

        elapsed = time.time() - start_time
        bachelor_count = len([p for p in self.programs.values() if p.program_type == 'BachelorProgram'])
        master_count = len([p for p in self.programs.values() if p.program_type == 'MasterProgram'])
        courses_with_instructor = len([c for c in self.courses.values() if c.taught_by])
        print("\n" + "=" * 60)
        print(f"Scraping completed in {elapsed:.2f} seconds")
        print(f"Organizations extracted: {len(self.organizations)}")
        print(f"Research Centers: {len([o for o in self.organizations.values() if o.org_type == 'ResearchCenter'])}")
        print(f"Chairs extracted: {len(self.chairs)}")
        print(f"Hiwi positions extracted: {len(self.hiwi_positions)}")
        print(f"Persons extracted: {len(self.persons)}")
        print(f"Minors extracted: {len(self.minors)}")
        print(f"Research Projects extracted: {len(self.research_projects)}")
        print(f"Programs extracted: {len(self.programs)} (Bachelor: {bachelor_count}, Master: {master_count})")
        print(f"Courses extracted: {len(self.courses)} ({courses_with_instructor} with instructor)")
        print("=" * 60)
    
    def save_results(self):
        """Save extracted data to JSON files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save organizations
        orgs_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / f"organizations_{timestamp}.json"
        with open(orgs_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uri: asdict(org) for uri, org in self.organizations.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved organizations to {orgs_file}")
        
        # Save chairs
        chairs_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / f"chairs_{timestamp}.json"
        with open(chairs_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uri: asdict(chair) for uri, chair in self.chairs.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved chairs to {chairs_file}")
        
        # Save Hiwi positions
        hiwi_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / f"hiwi_positions_{timestamp}.json"
        with open(hiwi_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uri: asdict(pos) for uri, pos in self.hiwi_positions.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved Hiwi positions to {hiwi_file}")
        
        # Save persons
        persons_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / f"persons_{timestamp}.json"
        with open(persons_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uri: asdict(person) for uri, person in self.persons.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved persons to {persons_file}")
        
        # Save programs
        programs_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / f"programs_{timestamp}.json"
        with open(programs_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uri: asdict(prog) for uri, prog in self.programs.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved programs to {programs_file}")

        # Save minors
        minors_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / f"minors_{timestamp}.json"
        with open(minors_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uri: asdict(minor) for uri, minor in self.minors.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved minors to {minors_file}")

        # Save research projects
        projects_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / f"research_projects_{timestamp}.json"
        with open(projects_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uri: asdict(proj) for uri, proj in self.research_projects.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved research projects to {projects_file}")

        # Save courses
        courses_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / f"courses_{timestamp}.json"
        with open(courses_file, 'w', encoding='utf-8') as f:
            json.dump(
                {uri: asdict(course) for uri, course in self.courses.items()},
                f, ensure_ascii=False, indent=2
            )
        print(f"Saved courses to {courses_file}")

        # Also save a combined file with latest data
        combined_file = Path(OUTPUT_CONFIG["raw_json_dir"]) / "latest.json"
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump({
                "metadata": {
                    "timestamp": timestamp,
                    "organization_count": len(self.organizations),
                    "research_center_count": len([o for o in self.organizations.values() if o.org_type == 'ResearchCenter']),
                    "chair_count": len(self.chairs),
                    "hiwi_position_count": len(self.hiwi_positions),
                    "person_count": len(self.persons),
                    "minor_count": len(self.minors),
                    "research_project_count": len(self.research_projects),
                    "course_count": len(self.courses),
                    "course_with_instructor_count": len([c for c in self.courses.values() if c.taught_by]),
                    "program_count": len(self.programs),
                },
                "organizations": {uri: asdict(org) for uri, org in self.organizations.items()},
                "chairs": {uri: asdict(chair) for uri, chair in self.chairs.items()},
                "hiwi_positions": {uri: asdict(pos) for uri, pos in self.hiwi_positions.items()},
                "persons": {uri: asdict(person) for uri, person in self.persons.items()},
                "minors": {uri: asdict(minor) for uri, minor in self.minors.items()},
                "research_projects": {uri: asdict(proj) for uri, proj in self.research_projects.items()},
                "courses": {uri: asdict(course) for uri, course in self.courses.items()},
                "programs": {uri: asdict(prog) for uri, prog in self.programs.items()},
            }, f, ensure_ascii=False, indent=2)
        print(f"Saved combined data to {combined_file}")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Leuphana KG Web Scraper')
    parser.add_argument('--sitemap', type=str,
                       help='Path to sitemap URLs file for comprehensive extraction')
    parser.add_argument('--max-persons', type=int,
                       help='Limit number of persons to extract (for testing)')

    args = parser.parse_args()

    scraper = LeuphanaScaper()
    scraper.run(sitemap_file=args.sitemap)