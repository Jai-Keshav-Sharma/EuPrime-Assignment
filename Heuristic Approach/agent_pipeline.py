"""
Agent-based LinkedIn extraction using OpenAI Agents with browser capabilities
This approach uses AI to navigate and extract data more naturally
"""

import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from dotenv import load_dotenv
import os

from openai import OpenAI
from enrichment_engine import (
    EmailEnricher, 
    PublicationEnricher, 
    CompanyEnricher,
    WorkModeInferencer
)
from scoring_engine import PropensityScorer

load_dotenv()


class AgentBasedPipeline:
    """Use AI agent with web browsing to extract LinkedIn profiles"""
    
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.email_enricher = EmailEnricher()
        self.pub_enricher = PublicationEnricher()
        self.company_enricher = CompanyEnricher()
        self.work_mode_inferencer = WorkModeInferencer()
        self.scorer = PropensityScorer()
    
    def extract_with_agent(self, url: str) -> dict:
        """Extract profile using AI agent with web browsing"""
        
        prompt = f"""Navigate to this LinkedIn profile and extract the following information:
{url}

Extract:
- name: Full name
- title: Current job title
- company: Current company name
- location: Personal location (city, state/country)
- about: Brief summary of their background and expertise
- experience: Key past roles
- skills: Relevant skills

Return the data in JSON format with these exact keys.
If you cannot access the profile, return an error message."""

        try:
            # Use GPT-4 with browsing capability
            response = self.client.chat.completions.create(
                model="gpt-4o",  # Use GPT-4 for better web understanding
                messages=[
                    {"role": "system", "content": "You are a data extraction expert. Extract structured information from web pages."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON from response
            if "{" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                json_str = content[start:end]
                profile_data = json.loads(json_str)
                profile_data['linkedin_url'] = url
                profile_data['extraction_status'] = 'success'
                return profile_data
            else:
                return {
                    'linkedin_url': url,
                    'extraction_status': 'failed',
                    'error': 'No JSON data in response',
                    'name': '', 'title': '', 'company': '', 'location': ''
                }
                
        except Exception as e:
            return {
                'linkedin_url': url,
                'extraction_status': 'failed',
                'error': str(e),
                'name': '', 'title': '', 'company': '', 'location': ''
            }
    
    async def process_batch(self, urls: list) -> pd.DataFrame:
        """Process a batch of URLs"""
        
        print(f"\n🔄 Processing batch of {len(urls)} profiles...")
        
        profiles = []
        for i, url in enumerate(urls):
            print(f"   [{i+1}/{len(urls)}] Extracting: {url[:60]}...")
            
            profile = self.extract_with_agent(url)
            
            if profile.get('extraction_status') != 'success':
                profiles.append({
                    'rank': 0,
                    'probability_score': 0,
                    'name': '',
                    'title': '',
                    'company': '',
                    'person_location': '',
                    'company_hq': '',
                    'work_mode': '',
                    'email': '',
                    'linkedin_url': url,
                    'extraction_status': 'failed'
                })
                continue
            
            # Check threshold
            if not self.scorer.passes_threshold(profile):
                print(f"      ⏭️ Skipping - not relevant role")
                continue
            
            # Enrich
            email = self.email_enricher.generate_email(
                profile.get('name', ''),
                profile.get('company', '')
            )
            
            pub_data = self.pub_enricher.search_publications(
                profile.get('name', ''),
                months_back=24
            )
            profile.update(pub_data)
            
            company_data = self.company_enricher.enrich_company(
                profile.get('company', ''),
                profile.get('location', '')
            )
            profile.update(company_data)
            
            work_mode = self.work_mode_inferencer.infer_work_mode(
                profile.get('title', ''),
                profile.get('location', ''),
                profile.get('about', '')
            )
            
            score_data = self.scorer.calculate_score(profile)
            
            enriched_profile = {
                'rank': 0,
                'probability_score': score_data['probability_score'],
                'name': profile.get('name', ''),
                'title': profile.get('title', ''),
                'company': profile.get('company', ''),
                'person_location': profile.get('location', ''),
                'company_hq': company_data.get('company_hq', ''),
                'work_mode': work_mode,
                'email': email,
                'linkedin_url': url,
                'extraction_status': 'success'
            }
            
            profiles.append(enriched_profile)
            
            await asyncio.sleep(2)  # Rate limiting
        
        return pd.DataFrame(profiles)
    
    async def run(self, input_csv="google.csv", output_csv="enriched_leads.csv", test_limit=20):
        """Run the pipeline"""
        
        print("\n" + "="*80)
        print("🚀 AGENT-BASED PIPELINE STARTED")
        print("="*80)
        
        input_df = pd.read_csv(input_csv)
        url_column = input_df.columns[0]
        all_urls = input_df[url_column].dropna().tolist()[:test_limit]
        
        print(f"📊 Processing {len(all_urls)} URLs...")
        
        batch_size = 10
        all_results = []
        
        for i in range(0, len(all_urls), batch_size):
            batch = all_urls[i:i+batch_size]
            batch_df = await self.process_batch(batch)
            all_results.append(batch_df)
            
            if i + batch_size < len(all_urls):
                print(f"⏳ Waiting 30 seconds...")
                await asyncio.sleep(30)
        
        # Combine and save
        final_df = pd.concat(all_results, ignore_index=True)
        final_df = final_df.sort_values('probability_score', ascending=False).reset_index(drop=True)
        
        scored_mask = (final_df['probability_score'] > 0) & (final_df['extraction_status'] == 'success')
        final_df.loc[scored_mask, 'rank'] = range(1, scored_mask.sum() + 1)
        
        output_columns = [
            'rank', 'probability_score', 'name', 'title', 'company',
            'person_location', 'company_hq', 'work_mode', 'email', 'linkedin_url'
        ]
        
        final_df[output_columns].to_csv(output_csv, index=False)
        
        print(f"\n✅ Complete! Results saved to {output_csv}")
        print(f"Successful: {scored_mask.sum()}/{len(final_df)}")


async def main():
    pipeline = AgentBasedPipeline()
    await pipeline.run(test_limit=20)


if __name__ == "__main__":
    asyncio.run(main())
