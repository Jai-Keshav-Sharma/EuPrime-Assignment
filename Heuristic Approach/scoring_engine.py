"""
Propensity Scoring Engine
Calculates probability score (0-100) using weighted signals
"""

from typing import Dict
import re


class PropensityScorer:
    """Calculate propensity to buy score (0-100)"""
    
    # Weight distribution (must sum to 100)
    WEIGHTS = {
        "role_relevance": 30,           # Director/Head of Toxicology, etc.
        "funding_stage": 20,             # Series A/B
        "tech_adoption": 15,             # Uses similar tech
        "nam_openness": 10,              # Open to NAMs
        "biotech_hub": 10,               # Located in hub
        "recent_publications": 40        # Recent relevant pubs (12-24 months)
    }
    
    # Target roles - HIGH relevance
    TARGET_ROLES = {
        "director of toxicology",
        "head of toxicology",
        "head of preclinical safety",
        "director of preclinical safety",
        "safety assessment",
        "hepatic toxicology",
        "investigative toxicology"
    }
    
    # Role keywords by priority
    ROLE_KEYWORDS = {
        "high": ["director", "head", "vp", "vice president", "chief", "lead"],
        "medium": ["senior", "principal", "manager"],
        "low": ["scientist", "associate", "specialist"]
    }
    
    # Relevant domains
    RELEVANT_DOMAINS = [
        "toxicology", "toxicologist", "safety assessment", "preclinical",
        "hepatic", "investigative", "dili", "liver"
    ]
    
    def passes_threshold(self, profile: Dict) -> bool:
        """
        Check if profile passes relevance threshold
        
        Args:
            profile: Profile dictionary
            
        Returns:
            bool: True if profile is relevant enough to score
        """
        title = profile.get("title", "").lower()
        about = profile.get("about", "").lower()
        
        # Must have relevant domain
        has_domain = any(domain in title or domain in about for domain in self.RELEVANT_DOMAINS)
        
        return has_domain
    
    def calculate_score(self, profile: Dict) -> Dict:
        """
        Calculate propensity score for a profile (0-100 scale)
        
        Args:
            profile: Profile dictionary with all enriched data
            
        Returns:
            Dict with probability_score (0-100) and breakdown
        """
        
        # Check threshold first
        if not self.passes_threshold(profile):
            return {
                "probability_score": 0,
                "score_breakdown": "Profile did not pass relevance threshold"
            }
        
        scores = {}
        
        # 1. Role Relevance (30 points max)
        scores["role_relevance"] = self._score_role(
            profile.get("title", ""),
            profile.get("about", "")
        ) * self.WEIGHTS["role_relevance"]
        
        # 2. Funding Stage (20 points max)
        scores["funding_stage"] = self._score_funding(
            profile.get("funding_stage", "")
        ) * self.WEIGHTS["funding_stage"]
        
        # 3. Tech Adoption (15 points max)
        scores["tech_adoption"] = self._score_tech_adoption(
            profile.get("about", ""),
            profile.get("skills", "")
        ) * self.WEIGHTS["tech_adoption"]
        
        # 4. NAM Openness (10 points max)
        scores["nam_openness"] = self._score_nam_openness(
            profile.get("about", ""),
            profile.get("skills", "")
        ) * self.WEIGHTS["nam_openness"]
        
        # 5. Biotech Hub (10 points max)
        scores["biotech_hub"] = self._score_location(
            profile.get("is_biotech_hub", False)
        ) * self.WEIGHTS["biotech_hub"]
        
        # 6. Recent Publications (40 points max) - HIGHEST WEIGHT
        scores["recent_publications"] = self._score_publications(
            profile.get("publication_count", 0),
            profile.get("has_recent_pubs", False)
        ) * self.WEIGHTS["recent_publications"]
        
        # Calculate weighted total (0-100 scale)
        total_score = sum(scores.values())
        
        return {
            "probability_score": round(total_score, 1),
            "score_breakdown": scores
        }
    
    def _score_role(self, title: str, about: str) -> float:
        """Score role relevance (0-1)"""
        title_lower = title.lower()
        about_lower = about.lower()
        
        # Check if it's a target role (perfect match)
        for target in self.TARGET_ROLES:
            if target in title_lower:
                return 1.0
        
        # Check for relevant domains
        domain_match = any(domain in title_lower or domain in about_lower 
                          for domain in self.RELEVANT_DOMAINS)
        
        if not domain_match:
            return 0.0
        
        # Check seniority level
        if any(keyword in title_lower for keyword in self.ROLE_KEYWORDS["high"]):
            return 1.0
        elif any(keyword in title_lower for keyword in self.ROLE_KEYWORDS["medium"]):
            return 0.6
        elif any(keyword in title_lower for keyword in self.ROLE_KEYWORDS["low"]):
            return 0.3
        
        return 0.5  # Default if in domain but unclear seniority
    
    def _score_funding(self, stage: str) -> float:
        """Score funding stage (0-1)"""
        stage_lower = stage.lower()
        
        if "series a" in stage_lower or "series b" in stage_lower:
            return 1.0
        elif "series c" in stage_lower or "seed" in stage_lower:
            return 0.6
        
        return 0.3  # Unknown
    
    def _score_tech_adoption(self, about: str, skills: str) -> float:
        """Score existing tech adoption (0-1)"""
        keywords = ["3d", "organoid", "organ-on-chip", "microphysiological", "spheroid"]
        
        combined = f"{about} {skills}".lower()
        matches = sum(1 for kw in keywords if kw in combined)
        
        return min(matches / 3, 1.0)
    
    def _score_nam_openness(self, about: str, skills: str) -> float:
        """Score openness to New Approach Methodologies (0-1)"""
        keywords = ["alternative methods", "nam", "reduce animal", "3rs", "in vitro"]
        
        combined = f"{about} {skills}".lower()
        matches = sum(1 for kw in keywords if kw in combined)
        
        return min(matches / 2, 1.0)
    
    def _score_location(self, is_hub: bool) -> float:
        """Score biotech hub location (0-1)"""
        return 1.0 if is_hub else 0.0
    
    def _score_publications(self, count: int, has_recent: bool) -> float:
        """Score recent publications (0-1) - HIGHEST IMPACT"""
        if not has_recent:
            return 0.0
        
        # Scale: 1-2 pubs = 0.5, 3-5 = 0.7, 6+ = 1.0
        if count >= 6:
            return 1.0
        elif count >= 3:
            return 0.7
        elif count >= 1:
            return 0.5
        
        return 0.0
