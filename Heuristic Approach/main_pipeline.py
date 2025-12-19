"""
Main Pipeline - Orchestrates the entire lead generation process
Runs extraction, enrichment, and scoring in batches with progress saving
"""

import asyncio
import pandas as pd
from pathlib import Path
from datetime import datetime
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from linkedin_extractor import LinkedInExtractor
from enrichment_engine import (
    EmailEnricher, 
    PublicationEnricher, 
    CompanyEnricher,
    WorkModeInferencer
)
from scoring_engine import PropensityScorer


class LeadGenerationPipeline:
    """Main pipeline orchestrator"""
    
    def __init__(
        self, 
        input_csv: str = "google.csv",
        output_csv: str = "enriched_leads.csv",
        linkedin_email: str = None,
        linkedin_password: str = None
    ):
        self.input_csv = input_csv
        self.output_csv = output_csv
        
        # Initialize components
        self.extractor = LinkedInExtractor(linkedin_email, linkedin_password)
        self.email_enricher = EmailEnricher()
        self.pub_enricher = PublicationEnricher()
        self.company_enricher = CompanyEnricher()
        self.work_mode_inferencer = WorkModeInferencer()
        self.scorer = PropensityScorer()
        
        # Configuration
        self.batch_size = 10
        self.delay_between_batches = 30  # Conservative: 30 seconds
    
    def load_existing_results(self) -> pd.DataFrame:
        """Load existing results if file exists"""
        if Path(self.output_csv).exists():
            try:
                df = pd.read_csv(self.output_csv)
                print(f"📂 Loaded {len(df)} existing results from {self.output_csv}")
                return df
            except Exception as e:
                print(f"⚠️ Could not load existing results: {e}")
                return pd.DataFrame()
        return pd.DataFrame()
    
    def get_processed_urls(self, existing_df: pd.DataFrame) -> set:
        """Get set of already processed URLs"""
        if 'linkedin_url' in existing_df.columns:
            return set(existing_df['linkedin_url'].dropna().tolist())
        return set()
    
    async def process_batch(self, urls: list) -> pd.DataFrame:
        """
        Process a single batch of URLs
        
        Args:
            urls: List of LinkedIn URLs to process
            
        Returns:
            DataFrame with processed results
        """
        print(f"\n{'='*80}")
        print(f"🔄 Processing batch of {len(urls)} profiles")
        print(f"{'='*80}")
        
        # Step 1: Extract LinkedIn profiles
        print("\n🔍 Step 1: Extracting LinkedIn profiles...")
        profiles = await self.extractor.extract_batch(
            urls, 
            batch_size=len(urls),  # Process all in this batch together
            delay_between_batches=0  # No delay within batch
        )
        
        # Step 2: Filter by threshold and enrich
        print("\n🔬 Step 2: Filtering and enriching profiles...")
        enriched_profiles = []
        
        for profile in profiles:
            if profile.get('extraction_status') != 'success':
                # Still save failed extractions
                enriched_profiles.append({
                    'rank': 0,
                    'probability_score': 0,
                    'name': profile.get('name', ''),
                    'title': profile.get('title', ''),
                    'company': profile.get('company', ''),
                    'person_location': profile.get('location', ''),
                    'company_hq': '',
                    'work_mode': '',
                    'email': '',
                    'linkedin_url': profile.get('linkedin_url', ''),
                    'extraction_status': 'failed',
                    'error': profile.get('error', 'Unknown error')
                })
                continue
            
            # Check if profile passes relevance threshold
            if not self.scorer.passes_threshold(profile):
                print(f"   ⏭️ Skipping {profile.get('name', 'Unknown')} - not relevant role")
                continue
            
            print(f"   ✅ Processing {profile.get('name', 'Unknown')}...")
            
            # Enrich with email
            email = self.email_enricher.generate_email(
                profile.get('name', ''),
                profile.get('company', '')
            )
            
            # Enrich with publications (only for threshold-passing profiles)
            pub_data = self.pub_enricher.search_publications(
                profile.get('name', ''),
                months_back=24
            )
            profile.update(pub_data)
            
            # Enrich with company data
            company_data = self.company_enricher.enrich_company(
                profile.get('company', ''),
                profile.get('location', '')
            )
            profile.update(company_data)
            
            # Infer work mode
            work_mode = self.work_mode_inferencer.infer_work_mode(
                profile.get('title', ''),
                profile.get('location', ''),
                profile.get('about', '')
            )
            
            # Calculate score
            score_data = self.scorer.calculate_score(profile)
            
            # Build final record matching sample_dashboard.csv format
            enriched_profile = {
                'rank': 0,  # Will be assigned after sorting all results
                'probability_score': score_data['probability_score'],
                'name': profile.get('name', ''),
                'title': profile.get('title', ''),
                'company': profile.get('company', ''),
                'person_location': profile.get('location', ''),
                'company_hq': company_data.get('company_hq', ''),
                'work_mode': work_mode,
                'email': email,
                'linkedin_url': profile.get('linkedin_url', ''),
                'extraction_status': 'success'
            }
            
            enriched_profiles.append(enriched_profile)
            
            # Small delay between enrichments
            await asyncio.sleep(1)
        
        # Convert to DataFrame
        batch_df = pd.DataFrame(enriched_profiles)
        
        print(f"\n   ✅ Batch complete: {len(batch_df)} profiles processed")
        
        return batch_df
    
    async def run(self, test_mode: bool = False, test_limit: int = 20):
        """
        Run the complete pipeline
        
        Args:
            test_mode: If True, only process first test_limit profiles
            test_limit: Number of profiles to process in test mode
        """
        print("\n" + "="*80)
        print("🚀 LEAD GENERATION PIPELINE STARTED")
        print("="*80)
        print(f"⏰ Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Load input data
        print(f"\n📂 Loading input data from {self.input_csv}...")
        input_df = pd.read_csv(self.input_csv)
        
        # Assume first column contains LinkedIn URLs
        url_column = input_df.columns[0]
        all_urls = input_df[url_column].dropna().tolist()
        
        # Load existing results
        existing_df = self.load_existing_results()
        processed_urls = self.get_processed_urls(existing_df)
        
        # Filter out already processed URLs
        urls_to_process = [url for url in all_urls if url not in processed_urls]
        
        if test_mode:
            urls_to_process = urls_to_process[:test_limit]
            print(f"🧪 TEST MODE: Processing first {test_limit} unprocessed profiles")
        
        print(f"📊 Total URLs in input: {len(all_urls)}")
        print(f"✅ Already processed: {len(processed_urls)}")
        print(f"🔄 To process: {len(urls_to_process)}")
        
        if not urls_to_process:
            print("\n✅ All profiles already processed!")
            return
        
        # Process in batches
        total_batches = (len(urls_to_process) + self.batch_size - 1) // self.batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * self.batch_size
            end_idx = min(start_idx + self.batch_size, len(urls_to_process))
            batch_urls = urls_to_process[start_idx:end_idx]
            
            print(f"\n{'='*80}")
            print(f"📦 BATCH {batch_num + 1}/{total_batches}")
            print(f"{'='*80}")
            
            # Process batch
            batch_df = await self.process_batch(batch_urls)
            
            # Append to existing results
            if len(existing_df) > 0:
                combined_df = pd.concat([existing_df, batch_df], ignore_index=True)
            else:
                combined_df = batch_df
            
            # Sort by probability score and assign ranks
            combined_df = combined_df.sort_values(
                'probability_score', 
                ascending=False
            ).reset_index(drop=True)
            
            # Assign ranks (only for successful extractions with score > 0)
            combined_df['rank'] = 0
            scored_mask = (combined_df['probability_score'] > 0) & (combined_df['extraction_status'] == 'success')
            combined_df.loc[scored_mask, 'rank'] = range(1, scored_mask.sum() + 1)
            
            # Save progress after each batch
            output_columns = [
                'rank', 'probability_score', 'name', 'title', 'company',
                'person_location', 'company_hq', 'work_mode', 'email', 'linkedin_url'
            ]
            
            combined_df[output_columns].to_csv(self.output_csv, index=False)
            
            print(f"\n💾 Progress saved to {self.output_csv}")
            print(f"   Total profiles in file: {len(combined_df)}")
            print(f"   Profiles with scores: {scored_mask.sum()}")
            
            # Update existing_df for next iteration
            existing_df = combined_df
            
            # Wait before next batch (except for last batch)
            if end_idx < len(urls_to_process):
                print(f"\n⏳ Waiting {self.delay_between_batches} seconds before next batch...")
                await asyncio.sleep(self.delay_between_batches)
        
        # Final summary
        print("\n" + "="*80)
        print("📊 PIPELINE SUMMARY")
        print("="*80)
        
        final_df = pd.read_csv(self.output_csv)
        successful = final_df[final_df['probability_score'] > 0]
        
        print(f"Total profiles processed: {len(final_df)}")
        print(f"Successful extractions: {len(successful)}")
        print(f"High Priority (≥80): {len(successful[successful['probability_score'] >= 80])}")
        print(f"Medium Priority (60-79): {len(successful[(successful['probability_score'] >= 60) & (successful['probability_score'] < 80)])}")
        print(f"Low Priority (<60): {len(successful[successful['probability_score'] < 60])}")
        
        if len(successful) > 0:
            print(f"\n🎯 Top 5 Leads:")
            print(successful[['rank', 'name', 'title', 'company', 'probability_score']].head().to_string(index=False))
        
        print(f"\n⏰ End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n✅ Pipeline completed successfully!")
        print(f"📁 Results saved to: {self.output_csv}")


async def main():
    """Main entry point"""
    
    # Initialize pipeline
    pipeline = LeadGenerationPipeline(
        input_csv="google.csv",
        output_csv="enriched_leads.csv",
        linkedin_email="***",
        linkedin_password="***"
    )
    
    # Run pipeline
    # Set test_mode=True to test with first 20 profiles
    await pipeline.run(test_mode=True, test_limit=20)
    
    # For full run, use:
    # await pipeline.run(test_mode=False)


if __name__ == "__main__":
    asyncio.run(main())
