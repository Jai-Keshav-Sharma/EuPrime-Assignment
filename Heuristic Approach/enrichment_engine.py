"""
Data Enrichment Engine
Handles email generation, publication search, and company enrichment
"""

import re
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta


class EmailEnricher:
    """Generate business emails using common patterns"""
    
    COMMON_PATTERNS = [
        "{first}.{last}@{domain}",
        "{first}{last}@{domain}",
        "{first_initial}{last}@{domain}",
    ]
    
    def generate_email(self, name: str, company: str, domain: Optional[str] = None) -> str:
        """Generate most likely business email"""
        
        if not name or not company:
            return ""
        
        # Clean and parse name
        name_parts = name.lower().split()
        if len(name_parts) < 2:
            return ""
        
        first = re.sub(r'[^a-z]', '', name_parts[0])
        last = re.sub(r'[^a-z]', '', name_parts[-1])
        first_initial = first[0] if first else ""
        
        # Get company domain
        if not domain:
            domain = self._infer_domain(company)
        
        # Generate most common pattern
        if first and last and domain:
            return f"{first}.{last}@{domain}"
        
        return ""
    
    def _infer_domain(self, company: str) -> str:
        """Infer company domain from name"""
        # Remove common suffixes
        company_clean = company.lower()
        company_clean = re.sub(r'\s+(inc|llc|ltd|corporation|corp|company|co)\b', '', company_clean)
        company_clean = re.sub(r'[^a-z0-9]', '', company_clean)
        
        if company_clean:
            return f"{company_clean}.com"
        
        return ""


class PublicationEnricher:
    """Fetch publications from PubMed"""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    # Keywords for liver toxicity / 3D models
    RELEVANT_KEYWORDS = [
        "liver toxicity",
        "DILI",
        "hepatotoxicity",
        "3D cell culture",
        "organoid",
        "microphysiological",
        "organ-on-chip",
        "spheroid"
    ]
    
    def search_publications(self, author_name: str, months_back: int = 24) -> Dict:
        """
        Search PubMed for relevant recent publications
        
        Args:
            author_name: Full name of author
            months_back: How many months back to search (default 24)
            
        Returns:
            Dict with publication count and status
        """
        
        if not author_name:
            return {"publication_count": 0, "has_recent_pubs": False}
        
        try:
            # Build query
            date_limit = (datetime.now() - timedelta(days=months_back*30)).strftime("%Y/%m/%d")
            
            # Combine author and keywords
            keyword_query = " OR ".join([f'"{kw}"[Title/Abstract]' for kw in self.RELEVANT_KEYWORDS])
            query = f'"{author_name}"[Author] AND ({keyword_query}) AND ("{date_limit}"[Date - Publication] : "3000"[Date - Publication])'
            
            # Search PubMed
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": 20,
                "retmode": "json"
            }
            
            response = requests.get(
                f"{self.BASE_URL}/esearch.fcgi",
                params=search_params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
            
            return {
                "publication_count": len(pmids),
                "has_recent_pubs": len(pmids) > 0
            }
            
        except Exception as e:
            print(f"⚠️ PubMed search error for {author_name}: {e}")
            return {
                "publication_count": 0,
                "has_recent_pubs": False
            }


class CompanyEnricher:
    """Enrich company information"""
    
    # Known biotech hubs
    BIOTECH_HUBS = {
        "boston", "cambridge", "san diego", "san francisco",
        "bay area", "basel", "munich", "london", "seattle",
        "research triangle", "raleigh", "durham"
    }
    
    def enrich_company(self, company_name: str, location: str) -> Dict:
        """Get company enrichment data"""
        
        return {
            "company_hq": self._infer_hq(company_name, location),
            "is_biotech_hub": self._is_biotech_hub(location),
            "funding_stage": self._infer_funding_stage(company_name)
        }
    
    def _infer_hq(self, company: str, person_location: str) -> str:
        """Infer company headquarters location"""
        # For now, assume HQ is same as person location
        # In production, use a company database
        return person_location if person_location else "Unknown"
    
    def _is_biotech_hub(self, location: str) -> bool:
        """Check if location is a known biotech hub"""
        if not location:
            return False
        
        location_lower = location.lower()
        return any(hub in location_lower for hub in self.BIOTECH_HUBS)
    
    def _infer_funding_stage(self, company: str) -> str:
        """Infer funding stage from company name (heuristic)"""
        if not company:
            return "Unknown"
        
        company_lower = company.lower()
        
        # Simple heuristics
        if any(term in company_lower for term in ["therapeutics", "bio", "pharma"]):
            return "Series A/B"
        
        return "Unknown"


class WorkModeInferencer:
    """Infer work mode (Remote/Onsite) from profile data"""
    
    REMOTE_KEYWORDS = ["remote", "distributed", "virtual", "work from home", "wfh"]
    
    def infer_work_mode(self, title: str, location: str, about: str) -> str:
        """
        Infer if position is remote or onsite
        
        Args:
            title: Job title
            location: Person's location
            about: About section
            
        Returns:
            "Remote" or "Onsite"
        """
        
        # Check for remote keywords
        combined_text = f"{title} {location} {about}".lower()
        
        if any(keyword in combined_text for keyword in self.REMOTE_KEYWORDS):
            return "Remote"
        
        return "Onsite"
