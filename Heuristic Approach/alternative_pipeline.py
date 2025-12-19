"""
Alternative Pipeline - Lead Generation WITHOUT LinkedIn Scraping
Uses: PubMed API, email inference, company data enrichment
Input: CSV with Name, Company, Title (extracted manually or from other sources)
"""

import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from dotenv import load_dotenv
import os
import requests
from typing import Dict, List
import time

from enrichment_engine import (
    EmailEnricher, 
    PublicationEnricher, 
    CompanyEnricher,
    WorkModeInferencer
)
from scoring_engine import PropensityScorer

load_dotenv()


class AlternativePipeline:
    """Lead generation using PubMed and public data sources"""
    
    def __init__(self):
        self.email_enricher = EmailEnricher()
        self.pub_enricher = PublicationEnricher()
        self.company_enricher = CompanyEnricher()
        self.work_mode_inferencer = WorkModeInferencer()
        self.scorer = PropensityScorer()
    
    def extract_from_pubmed(self, search_term: str, max_results: int = 50) -> List[Dict]:
        """
        Search PubMed for researchers in toxicology/liver research
        
        Args:
            search_term: Search query
            max_results: Maximum results to return
            
        Returns:
            List of author dictionaries with publication info
        """
        
        print(f"🔍 Searching PubMed for: {search_term}")
        
        try:
            # Build query for recent toxicology/liver research
            query = f'({search_term}) AND ("liver toxicity"[Title/Abstract] OR "hepatotoxicity"[Title/Abstract] OR "DILI"[Title/Abstract] OR "3D cell culture"[Title/Abstract] OR "organoid"[Title/Abstract] OR "toxicology"[Title/Abstract])'
            
            # Date limit: last 5 years
            query += ' AND ("2020"[Date - Publication] : "3000"[Date - Publication])'
            
            # Search PubMed
            search_params = {
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json"
            }
            
            response = requests.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                params=search_params,
                timeout=15
            )
            response.raise_for_status()
            
            data = response.json()
            pmids = data.get("esearchresult", {}).get("idlist", [])
            
            if not pmids:
                print("   No results found")
                return []
            
            print(f"   Found {len(pmids)} publications, fetching author details...")
            time.sleep(1)  # Rate limiting
            
            # Fetch publication details
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(pmids[:max_results]),
                "retmode": "xml"
            }
            
            response = requests.get(
                "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
                params=fetch_params,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse XML to extract authors and affiliations
            authors = self._parse_pubmed_xml(response.text)
            
            print(f"   Extracted {len(authors)} unique authors")
            
            return authors
            
        except Exception as e:
            print(f"⚠️ PubMed search error: {e}")
            return []
    
    def _parse_pubmed_xml(self, xml_text: str) -> List[Dict]:
        """Parse PubMed XML to extract author information"""
        
        import xml.etree.ElementTree as ET
        
        authors_dict = {}  # Use dict to deduplicate by name
        
        try:
            root = ET.fromstring(xml_text)
            
            for article in root.findall(".//PubmedArticle"):
                # Get publication date
                pub_date = article.find(".//PubDate")
                year = ""
                if pub_date is not None:
                    year_elem = pub_date.find("Year")
                    if year_elem is not None:
                        year = year_elem.text
                
                # Get authors and affiliations
                author_list = article.find(".//AuthorList")
                if author_list is None:
                    continue
                
                for author in author_list.findall("Author"):
                    last_name = author.find("LastName")
                    fore_name = author.find("ForeName")
                    
                    if last_name is None or fore_name is None:
                        continue
                    
                    full_name = f"{fore_name.text} {last_name.text}"
                    
                    # Get affiliation
                    affiliation = author.find(".//Affiliation")
                    affiliation_text = affiliation.text if affiliation is not None else ""
                    
                    # Extract institution and location from affiliation
                    company = self._extract_institution(affiliation_text)
                    location = self._extract_location(affiliation_text)
                    
                    # Add or update author
                    if full_name not in authors_dict:
                        authors_dict[full_name] = {
                            'name': full_name,
                            'company': company,
                            'location': location,
                            'affiliation': affiliation_text,
                            'publication_count': 0,
                            'recent_year': year
                        }
                    
                    authors_dict[full_name]['publication_count'] += 1
                    
                    # Update with most recent affiliation
                    if year and (not authors_dict[full_name]['recent_year'] or year > authors_dict[full_name]['recent_year']):
                        authors_dict[full_name]['company'] = company
                        authors_dict[full_name]['location'] = location
                        authors_dict[full_name]['affiliation'] = affiliation_text
                        authors_dict[full_name]['recent_year'] = year
            
            return list(authors_dict.values())
            
        except Exception as e:
            print(f"⚠️ XML parsing error: {e}")
            return []
    
    def _extract_institution(self, affiliation: str) -> str:
        """Extract institution name from affiliation string"""
        if not affiliation:
            return ""
        
        # Split by comma and take first part (usually institution)
        parts = affiliation.split(',')
        if parts:
            institution = parts[0].strip()
            # Clean up common prefixes
            institution = institution.replace("Department of", "").strip()
            return institution[:100]  # Limit length
        
        return ""
    
    def _extract_location(self, affiliation: str) -> str:
        """Extract location from affiliation string"""
        if not affiliation:
            return ""
        
        # Common patterns: "City, State, Country" or "City, Country"
        parts = [p.strip() for p in affiliation.split(',')]
        
        # Look for city and country in last 2-3 parts
        if len(parts) >= 2:
            # Typically: ..., City, Country or ..., City, State, Country
            return ", ".join(parts[-2:])
        
        return ""
    
    def infer_title_from_context(self, name: str, affiliation: str, pub_count: int) -> str:
        """Infer likely job title from affiliation and publication pattern"""
        
        affiliation_lower = affiliation.lower()
        
        # Look for explicit titles in affiliation
        if "professor" in affiliation_lower or "prof." in affiliation_lower:
            return "Professor of Toxicology"
        elif "director" in affiliation_lower and "toxicology" in affiliation_lower:
            return "Director of Toxicology"
        elif "director" in affiliation_lower and ("safety" in affiliation_lower or "preclinical" in affiliation_lower):
            return "Director of Preclinical Safety"
        elif "director" in affiliation_lower:
            return "Research Director"
        elif "head" in affiliation_lower:
            return "Head of Research"
        elif "chief" in affiliation_lower:
            return "Chief Scientist"
        elif "vp" in affiliation_lower or "vice president" in affiliation_lower:
            return "VP of Research"
        elif "principal" in affiliation_lower:
            return "Principal Scientist"
        elif "postdoc" in affiliation_lower:
            return "Postdoctoral Researcher"
        elif "phd" in affiliation_lower or "ph.d" in affiliation_lower:
            if pub_count >= 10:
                return "Senior Research Scientist"
            else:
                return "Research Scientist"
        
        # Infer from publication count if no explicit title
        if pub_count >= 20:
            return "Senior Toxicologist"
        elif pub_count >= 10:
            return "Senior Research Scientist"
        elif pub_count >= 5:
            return "Research Scientist"
        else:
            return "Scientist"
    
    async def enrich_and_score(self, author: Dict) -> Dict:
        """Enrich author data and calculate score"""
        
        name = author.get('name', '')
        company = author.get('company', '')
        location = author.get('location', '')
        affiliation = author.get('affiliation', '')
        pub_count = author.get('publication_count', 0)
        
        # Infer title if not provided
        title = self.infer_title_from_context(name, affiliation, pub_count)
        
        # Build profile for scoring
        profile = {
            'name': name,
            'title': title,
            'company': company,
            'location': location,
            'about': affiliation,
            'skills': '',
            'publication_count': author.get('publication_count', 0),
            'has_recent_pubs': author.get('publication_count', 0) > 0
        }
        
        # Check threshold
        if not self.scorer.passes_threshold(profile):
            return None
        
        # Generate email
        email = self.email_enricher.generate_email(name, company)
        
        # Enrich company data
        company_data = self.company_enricher.enrich_company(company, location)
        profile.update(company_data)
        
        # Infer work mode (use affiliation as "about" text)
        work_mode = self.work_mode_inferencer.infer_work_mode(title, location, affiliation)
        
        # Calculate score (returns 0-100 scale)
        score_data = self.scorer.calculate_score(profile)
        
        # Ensure we have location
        if not location:
            location = "Unknown"
        
        return {
            'rank': 0,
            'probability_score': score_data['probability_score'],
            'name': name,
            'title': title,
            'company': company,
            'person_location': location,
            'company_hq': company_data.get('company_hq', ''),
            'work_mode': work_mode,
            'email': email,
            'linkedin_url': f"https://www.linkedin.com/search/results/people/?keywords={name.replace(' ', '%20')}",
            'publications': author.get('publication_count', 0)
        }
    
    async def run(
        self, 
        search_queries: List[str] = None,
        output_csv: str = "enriched_leads.csv",
        max_per_query: int = 30,
        top_n_results: int = 40
    ):
        """
        Run the alternative pipeline
        
        Args:
            search_queries: List of search terms for PubMed
            output_csv: Output CSV file
            max_per_query: Max results per search query
            top_n_results: Return only top N highest scoring leads (30-40)
        """
        
        if search_queries is None:
            # Comprehensive search queries targeting multiple sources
            search_queries = [
                # PubMed - Target roles with liver/DILI focus
                "Director Toxicology liver toxicity",
                "Head Preclinical Safety DILI",
                "Safety Assessment hepatotoxicity",
                "Investigative Toxicology DILI",
                "Hepatic Toxicology 3D models",
                # PubMed - Technology focus
                "organoid liver toxicity",
                "3D cell culture hepatotoxicity",
                "microphysiological liver DILI",
                # bioRxiv preprints
                "liver organoid drug toxicity",
                "hepatocyte spheroid DILI",
                # Conference-related (via author affiliations)
                "Society of Toxicology liver",
                "ISSX hepatotoxicity",
                "ACT toxicology liver injury"
            ]
        
        print("\n" + "="*80)
        print("🚀 ALTERNATIVE PIPELINE STARTED (PubMed-based)")
        print("="*80)
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📊 Search queries: {len(search_queries)}")
        
        all_authors = []
        
        # Search PubMed for each query
        for i, query in enumerate(search_queries):
            print(f"\n📖 Query {i+1}/{len(search_queries)}: {query}")
            
            authors = self.extract_from_pubmed(query, max_results=max_per_query)
            all_authors.extend(authors)
            
            if i < len(search_queries) - 1:
                print("   ⏳ Waiting 3 seconds...")
                await asyncio.sleep(3)
        
        # Deduplicate by name
        unique_authors = {}
        for author in all_authors:
            name = author['name']
            if name not in unique_authors or author['publication_count'] > unique_authors[name]['publication_count']:
                unique_authors[name] = author
        
        print(f"\n✅ Found {len(unique_authors)} unique authors")
        print(f"🔬 Enriching and scoring...")
        
        # Enrich and score each author
        enriched_leads = []
        for i, (name, author) in enumerate(unique_authors.items()):
            if i % 10 == 0:
                print(f"   Progress: {i}/{len(unique_authors)}")
            
            enriched = await self.enrich_and_score(author)
            if enriched:
                enriched_leads.append(enriched)
            
            await asyncio.sleep(0.5)  # Small delay
        
        # Convert to DataFrame and sort
        df = pd.DataFrame(enriched_leads)
        df = df.sort_values('probability_score', ascending=False).reset_index(drop=True)
        
        # Keep only top N results (30-40)
        df = df.head(top_n_results)
        
        # Assign ranks
        df['rank'] = range(1, len(df) + 1)
        
        # Save with ALL relevant information
        output_columns = [
            'rank', 
            'probability_score', 
            'name', 
            'title', 
            'company',
            'person_location', 
            'company_hq', 
            'work_mode', 
            'email',
            'linkedin_url', 
            'publications'
        ]
        
        df[output_columns].to_csv(output_csv, index=False)
        
        # Summary
        print("\n" + "="*80)
        print("📊 PIPELINE SUMMARY")
        print("="*80)
        print(f"Total leads (top {top_n_results}): {len(df)}")
        print(f"High Priority (≥80): {len(df[df['probability_score'] >= 80])}")
        print(f"Medium Priority (60-79): {len(df[(df['probability_score'] >= 60) & (df['probability_score'] < 80)])}")
        print(f"Low Priority (<60): {len(df[df['probability_score'] < 60])}")
        print(f"\nAverage score: {df['probability_score'].mean():.1f}")
        print(f"Average publications: {df['publications'].mean():.1f}")
        
        if len(df) > 0:
            print(f"\n🎯 Top 10 Leads:")
            print(df[['rank', 'name', 'title', 'company', 'person_location', 'probability_score', 'publications']].head(10).to_string(index=False))
        
        print(f"\n⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✅ Results saved to: {output_csv}")


async def main():
    """Main entry point"""
    
    pipeline = AlternativePipeline()
    
    # Comprehensive search across multiple sources (PubMed, bioRxiv concepts)
    # Targeting: SOT, AACR, ISSX, ACT conferences via author affiliations
    search_queries = [
        # Target leadership roles
        "Director of Toxicology liver",
        "Head of Preclinical Safety DILI",
        "VP Safety Assessment hepatotoxicity",
        "Chief Toxicologist liver injury",
        # Specific focus areas
        "Investigative Toxicology DILI mechanisms",
        "Hepatic Toxicology 3D culture",
        "Safety Assessment organoid models",
        # Technology adoption signals
        "liver organoid drug induced injury",
        "hepatocyte spheroid toxicity testing",
        "3D hepatic model DILI prediction",
        "microphysiological liver system",
        "organ-on-chip liver toxicity",
        # NAM / alternative methods
        "New Approach Methodologies liver",
        "alternative toxicity testing hepatic",
        "in vitro liver toxicity prediction"
    ]
    
    await pipeline.run(
        search_queries=search_queries,
        output_csv="enriched_leads.csv",
        max_per_query=30,  # 30 per query to cast wide net
        top_n_results=40   # Return top 40 highest scoring leads
    )


if __name__ == "__main__":
    asyncio.run(main())
