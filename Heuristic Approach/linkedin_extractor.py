"""
LinkedIn Profile Extractor with Playwright + LLM
Supports both logged-in and non-logged-in modes
"""

import asyncio
from playwright.async_api import async_playwright, Browser, BrowserContext
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
import json
from typing import Dict, Optional, List
import time
from datetime import datetime


class LinkedInExtractor:
    def __init__(self, login_email: Optional[str] = None, login_password: Optional[str] = None):
        """
        Initialize LinkedIn extractor
        
        Args:
            login_email: LinkedIn email (optional)
            login_password: LinkedIn password (optional)
        """
        self.login_email = login_email
        self.login_password = login_password
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        self.extraction_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a data extraction expert. Extract structured information from LinkedIn profile text.

Extract these fields:
- name: Full name
- title: Current job title
- company: Current company name
- location: Personal location (city, state/country)
- about: Summary/about section (first 500 chars)
- experience: Brief description of past roles
- skills: Relevant skills (comma-separated)

Return ONLY valid JSON with these exact keys. If a field is not found, use empty string.
Example: {{"name": "John Doe", "title": "Director of Toxicology", "company": "BioTech Inc", "location": "Boston, MA", "about": "...", "experience": "...", "skills": "..."}}"""),
            ("user", "Extract information from this LinkedIn profile:\n\n{text_content}")
        ])
    
    async def login_to_linkedin(self, page) -> bool:
        """
        Login to LinkedIn if credentials provided
        
        Returns:
            bool: True if login successful or not needed, False if failed
        """
        if not self.login_email or not self.login_password:
            return True  # No login needed
        
        try:
            print("🔐 Logging in to LinkedIn...")
            
            await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            await page.wait_for_selector("#username", timeout=10000)
            
            # Enter credentials
            await page.fill("#username", self.login_email)
            await page.fill("#password", self.login_password)
            await page.click('button[type="submit"]')
            
            # Wait for navigation
            await page.wait_for_url("https://www.linkedin.com/feed/", timeout=15000)
            
            print("✅ Login successful!")
            return True
            
        except Exception as e:
            print(f"❌ Login failed: {e}")
            return False
    
    async def extract_profile(self, url: str, context: BrowserContext, max_retries: int = 3) -> Dict:
        """
        Extract data from a single LinkedIn profile with retry logic
        
        Args:
            url: LinkedIn profile URL
            context: Browser context
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict with profile data
        """
        for attempt in range(max_retries):
            try:
                page = await context.new_page()
                
                # Navigate with timeout
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Wait for profile to load
                try:
                    await page.wait_for_selector("h1", timeout=10000)
                except:
                    # If selector not found, continue anyway (might be different layout)
                    pass
                
                # Add small delay to let content render
                await asyncio.sleep(2)
                
                # Extract text content
                text_content = await page.evaluate("""
                    () => {
                        // Remove scripts and styles
                        const scripts = document.querySelectorAll('script, style');
                        scripts.forEach(s => s.remove());
                        
                        return document.body.innerText;
                    }
                """)
                
                await page.close()
                
                # Use LLM to structure the data
                response = await self.llm.ainvoke(
                    self.extraction_prompt.format(text_content=text_content[:8000])
                )
                
                # Parse JSON response
                profile_data = json.loads(response.content)
                profile_data['linkedin_url'] = url
                profile_data['extraction_status'] = 'success'
                profile_data['extracted_at'] = datetime.now().isoformat()
                
                return profile_data
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ JSON parse error for {url}, retrying... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    return {
                        'linkedin_url': url,
                        'extraction_status': 'failed',
                        'error': f'JSON parse error after {max_retries} attempts',
                        'name': '',
                        'title': '',
                        'company': '',
                        'location': ''
                    }
            
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"⚠️ Error extracting {url}, retrying... (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(5 * (attempt + 1))  # Exponential backoff
                    continue
                else:
                    return {
                        'linkedin_url': url,
                        'extraction_status': 'failed',
                        'error': str(e),
                        'name': '',
                        'title': '',
                        'company': '',
                        'location': ''
                    }
        
        # Should never reach here, but just in case
        return {
            'linkedin_url': url,
            'extraction_status': 'failed',
            'error': 'Unknown error',
            'name': '',
            'title': '',
            'company': '',
            'location': ''
        }
    
    async def extract_batch(
        self, 
        urls: List[str], 
        batch_size: int = 10,
        delay_between_batches: int = 30
    ) -> List[Dict]:
        """
        Extract profiles in batches with conservative rate limiting
        
        Args:
            urls: List of LinkedIn URLs
            batch_size: Number of profiles per batch
            delay_between_batches: Seconds to wait between batches
            
        Returns:
            List of extracted profile dictionaries
        """
        results = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(
                headless=True,  # Set to False for debugging
                args=['--disable-blink-features=AutomationControlled']
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            # Login if credentials provided
            if self.login_email and self.login_password:
                login_page = await context.new_page()
                login_success = await self.login_to_linkedin(login_page)
                await login_page.close()
                
                if not login_success:
                    print("⚠️ Continuing without login...")
            
            # Process in batches
            total_batches = (len(urls) + batch_size - 1) // batch_size
            
            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(urls))
                batch = urls[start_idx:end_idx]
                
                print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch)} profiles)...")
                
                # Process batch with individual delays between profiles
                batch_results = []
                for i, url in enumerate(batch):
                    print(f"   [{i+1}/{len(batch)}] Extracting: {url[:60]}...")
                    
                    result = await self.extract_profile(url, context, max_retries=3)
                    batch_results.append(result)
                    
                    # Small delay between individual profiles
                    if i < len(batch) - 1:
                        await asyncio.sleep(3)  # 3 seconds between profiles
                
                results.extend(batch_results)
                
                # Count successes in this batch
                success_count = sum(1 for r in batch_results if r.get('extraction_status') == 'success')
                print(f"   ✅ Batch complete: {success_count}/{len(batch)} successful")
                
                # Conservative delay between batches
                if end_idx < len(urls):
                    print(f"   ⏳ Waiting {delay_between_batches} seconds before next batch...")
                    await asyncio.sleep(delay_between_batches)
            
            await browser.close()
        
        return results
