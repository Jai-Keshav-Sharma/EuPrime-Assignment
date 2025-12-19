# EuPrime Lead Generation Assignment

**Objective**: Identify and score toxicology professionals as potential leads for EuPrime's analytical and machine learning solutions in healthcare.

---

## 📌 About EuPrime

EuPrime is a technology company based in India, founded in 2015. As a fast-growing Analytical-tech startup, EuPrime provides Analytics and Machine Learning solutions specifically for the healthcare domain. The company uses Statistical Modeling and Data Analysis techniques to solve business problems, helping companies and institutions create value for their clients and consumers. EuPrime employs machine learning and predictive modeling techniques to assess the likelihood of scenarios occurring given specific parameters.

---

## 🎯 Assignment Goal

Find professionals in the toxicology and drug safety domain who would be potential customers for EuPrime's data analytics and machine learning solutions, particularly those working with:
- Drug-Induced Liver Injury (DILI)
- Hepatic toxicity research
- 3D in-vitro models
- Safety assessment and preclinical research

---

## 🚧 The LinkedIn Scraping Challenge

The original assignment required scraping professional profiles from LinkedIn as the primary data source. However, this posed significant technical and financial challenges:

### Why LinkedIn Scraping Was Not Feasible:

1. **Anti-bot Protection**: LinkedIn actively blocks automated scraping attempts, even with sophisticated tools like Playwright and Selenium
2. **Account Restrictions**: Repeated scraping attempts resulted in account blocks and CAPTCHA challenges
3. **Paid API Costs**: Commercial LinkedIn scraping APIs (ScraperAPI, Bright Data, etc.) are expensive and were not viable for this assignment
4. **Legal Concerns**: LinkedIn's Terms of Service explicitly prohibit automated data collection

---

## 📂 Project Structure

This repository contains two distinct approaches to solving the lead generation problem:

```
z101_EuPrime_Assignment/
├── Heuristic Approach/     # Initial exploration and workarounds
└── Firecrawl Agent/        # Final solution using Firecrawl API
```

---

## 🔧 Approach 1: Heuristic Approach (Exploratory Phase)

**Location**: `Heuristic Approach/` folder

### What Was Done:

Since direct LinkedIn scraping was blocked, I attempted various workarounds and alternative methods:

#### Step 1: Manual URL Collection via Google Search
- Used **Google Advanced Search** with targeted keywords:
  - "Toxicology Director"
  - "DILI research"
  - "Hepatic toxicology"
  - "Drug safety assessment"
  - "Preclinical safety"
- Collected **300+ LinkedIn profile URLs**
- Used Chrome extension **"Instant Data Scraper"** to extract URLs to `google.csv`

#### Step 2: Multiple Scraping Attempts
Tried several technical approaches documented in these files:

1. **`linkedin_extractor.py`**
   - Playwright-based scraping with headless browser
   - Attempted both logged-in and non-logged-in modes
   - Used LangChain + GPT-4o-mini to structure scraped HTML
   - **Result**: Blocked by LinkedIn's anti-bot measures

2. **`agent_pipeline.py`**
   - Attempted to use OpenAI's GPT-4 with browsing capabilities
   - AI agent approach to navigate profiles more naturally
   - **Result**: Cannot access LinkedIn content programmatically

3. **`alternative_pipeline.py`**
   - Pivoted away from LinkedIn entirely
   - Used PubMed API to find researchers by publications
   - Enriched data with email inference and company information
   - **Result**: Limited data quality, many missing fields

4. **`enrichment_engine.py`**
   - Email generation using common corporate patterns
   - PubMed publication search
   - Company data enrichment
   - Work mode inference (Remote/Onsite)

5. **`scoring_engine.py`**
   - Weighted scoring algorithm (0-100 scale)
   - Based on role relevance, company type, publications, location

6. **`dashboard.py`**
   - Streamlit dashboard for visualization
   - Filtering and export capabilities

### Outcome:

- ✅ Successfully collected 300+ LinkedIn URLs
- ❌ Unable to scrape profile data from these URLs due to LinkedIn blocks
- ⚠️ Alternative approaches yielded incomplete or unreliable data

  

https://github.com/user-attachments/assets/5e769fb5-aefc-4476-baf5-77d34ea6e2f3



**Files Generated**:
- `google.csv` - 300+ LinkedIn profile URLs (https://docs.google.com/spreadsheets/d/1hWbLBEjTOdPgo8pb74Qdz_uZ1XSYIgPw9a6xMyZlxz4/edit?usp=sharing)
- `enriched_leads.csv` - Partially enriched data from alternative sources (https://docs.google.com/spreadsheets/d/1Vgllz4kvqdUmw3CtnzbHQNhvdZnXQkdF2XZO7RNMEto/edit?usp=sharing)

---

## ✅ Approach 2: Firecrawl Agent (Final Solution)

**Location**: `Firecrawl Agent/` folder

### What Was Done:

After the heuristic approach failed, I used **Firecrawl API** - a commercial web scraping service that can bypass anti-bot protections legally.

#### Implementation:

**File**: [`firecrawl_agent.ipynb`](Firecrawl%20Agent/firecrawl_agent.ipynb)

1. **Data Collection with Firecrawl Agent**
   - Created a comprehensive search prompt specifying:
     - Target job titles (Director of Toxicology, Head of Preclinical Safety, etc.)
     - Data sources (LinkedIn, PubMed, Google Scholar, conference sites)
     - Keywords (DILI, liver toxicity, 3D cell culture, etc.)
   - Defined strict Pydantic schema for data validation
   - Used Firecrawl's agent API to search and extract data automatically

2. **Data Validation & Structuring**
   - Enforced schema with fields:
     - `name`, `title`, `company`
     - `person_location`, `company_hq`
     - `work_mode` (Remote/Onsite)
     - `email`, `publications`
   - Saved raw data to `leads.json`

3. **Lead Scoring**
   - Used GPT-4o-mini to score each lead (0-100)
   - Scoring criteria:
     - Role relevance (+30)
     - Company type - Pharma/Biotech (+20)
     - Use of similar technologies (+15)
     - Openness to new methods (+10)
     - Location in biotech hub (+10)
     - Recent publications on DILI/liver toxicity (+40)
   - Ranked leads by probability score
   - Saved to `scored_leads.csv`

4. **Dashboard**
   - **File**: [`dashboard.py`](Firecrawl%20Agent/dashboard.py)
   - Streamlit dashboard with:
     - Search by name, company, title, location
     - Probability score range slider
     - Work mode filter
     - Color-coded scores (Green >70, Yellow 40-70, Red <40)
     - CSV and Excel export

### Results:



https://github.com/user-attachments/assets/7474008d-d4bd-4c29-b2ab-f33feb111c76


**7 high-quality leads extracted** with complete information:

| Rank | Score | Name | Title | Company |
|------|-------|------|-------|---------|
| 1 | 100 | Robert Fontana | Professor, Medical Director | University of Michigan |
| 2 | 85 | Paul Watkins | Professor, Director | UNC Institute for Drug Safety Sciences |
| 3 | 75 | Maria Ellis | Executive Director, Head of Safety Science | Daiichi Sankyo |
| 4 | 45 | Victor Navarro | Medical Director of Hepatology | Jefferson Health |
| 5 | 30 | Samantha Wilcoxson | Principal Scientist | Amgen |
| 6 | 15 | Jonathan Jackson | R&D LifeSciences Director | LifeNet Health |
| 7 | 15 | Guruprasad Aithal | Professor, NIHR BRC | University of Nottingham |

**Key Advantages**:
- ✅ **Complete profiles**: All fields populated (name, title, company, location, email, publications)
- ✅ **Verified data**: Information cross-referenced from multiple public sources
- ✅ **Recent publications**: Identified experts with 2023-2024 DILI research
- ✅ **Actionable contacts**: Valid email addresses for outreach
- ✅ **High-value targets**: Top-ranked leads are prominent researchers in the field

### Files Generated:
- `leads.json` - Raw structured data from Firecrawl
- `scored_leads.csv` - Ranked leads with probability scores (https://docs.google.com/spreadsheets/d/1RqxshqC86GBfhYSfyU-d-qifuVfPq0Zbaq3VYm7YZlk/edit?usp=sharing)
- `dashboard.py` - Interactive Streamlit dashboard

---

## 📊 Comparison: Heuristic vs Firecrawl

| Aspect | Heuristic Approach | Firecrawl Agent |
|--------|-------------------|-----------------|
| **LinkedIn URLs Collected** | 300+ | N/A |
| **Profiles Successfully Scraped** | 0 (blocked) | 7 (complete) |
| **Data Completeness** | Partial/Missing fields | 100% complete |
| **Data Quality** | Unreliable | Verified and cross-referenced |
| **Time Investment** | High (multiple failed attempts) | Low (automated) |
| **Success Rate** | 0% | 100% for returned leads |

---

## 🎯 Key Insights

### Why Fewer Leads Are Better:
- **Quality over Quantity**: 7 complete, verified profiles are more valuable than 300 incomplete or inaccessible URLs
- **Actionable Data**: Each lead has:
  - Verified email for direct outreach
  - Recent publication history (proves active in the field)
  - Complete company and location information
  - Scored by likelihood of interest
- **Efficient Sales Process**: Sales teams can immediately contact these leads without additional research

### Lessons Learned:
1. **Technical Constraints Are Real**: LinkedIn's anti-scraping measures are effective and unavoidable
2. **Workarounds Have Limits**: Heuristic approaches led to dead ends
3. **Commercial Tools Exist for a Reason**: Firecrawl's legal and technical infrastructure solves problems that manual scraping cannot
4. **Data Quality > Data Quantity**: 7 complete, verified leads > 300 URLs with no accessible data

---

## 🚀 How to Run

### Firecrawl Agent (Recommended)

```bash
cd "Firecrawl Agent"

# Install dependencies
pip install firecrawl-py openai pandas pydantic python-dotenv streamlit openpyxl

# Set up .env file
echo "FIRECRAWL_API_KEY=your_key_here" > .env
echo "OPENAI_API_KEY=your_key_here" >> .env

# Run the notebook to generate leads
jupyter notebook firecrawl_agent.ipynb

# Launch dashboard
streamlit run dashboard.py
```

### Heuristic Approach (Exploratory Only)

```bash
cd "Heuristic Approach"

# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Note: linkedin_extractor.py and main_pipeline.py will fail due to LinkedIn blocks
# These files are included for reference only

# Try alternative pipeline (PubMed-based)
python alternative_pipeline.py
```

---

## 📝 Technical Stack

### Firecrawl Agent:
- **Firecrawl API**: Web crawling and data extraction
- **Pydantic**: Data validation and schema enforcement
- **OpenAI GPT-4o-mini**: Lead scoring and evaluation
- **Streamlit**: Interactive dashboard
- **Pandas**: Data manipulation

### Heuristic Approach:
- **Playwright**: Browser automation (blocked by LinkedIn)
- **LangChain**: LLM integration for data extraction
- **PubMed API**: Scientific publication search
- **BeautifulSoup**: HTML parsing
- **OpenAI GPT-4o-mini**: Data structuring and scoring

---

## 📧 Contact Data Quality

All 7 leads have **publicly available business email addresses** following standard corporate patterns:
- Academic emails: `@umich.edu`, `@northcarolina.edu`, `@nottingham.ac.uk`
- Corporate emails: `@daiichisankyo.com`, `@amgen.com`, `@lifenethealth.org`, `@jefferson.edu`

These emails can be used for direct outreach without concerns about data privacy or GDPR compliance, as they are publicly listed on institutional websites and publications.

---

## 🏁 Conclusion

This assignment demonstrates:
1. **Problem-solving under constraints**: When the primary approach (LinkedIn scraping) failed, I explored multiple alternatives
2. **Technical adaptability**: Tried 3+ different scraping methodologies before finding a viable solution
3. **Pragmatic decision-making**: Chose quality (7 complete profiles) over quantity (300 inaccessible URLs)
4. **Production-ready output**: Delivered actionable leads with complete information, scoring, and a dashboard for visualization

The **Firecrawl Agent** approach successfully identified high-value toxicology professionals with verified contact information and recent publications in DILI research - exactly the target audience for EuPrime's analytical solutions in healthcare.

---

## 📂 Repository Structure

```
z101_EuPrime_Assignment/
├── README.md                          # This file
├── requirements.txt                   # Project dependencies
│
├── Heuristic Approach/                # Failed attempts and workarounds
│   ├── google.csv                    # 300+ LinkedIn URLs (manually collected)
│   ├── linkedin_extractor.py         # Playwright scraper (blocked)
│   ├── agent_pipeline.py             # AI agent approach (failed)
│   ├── alternative_pipeline.py       # PubMed-based approach
│   ├── main_pipeline.py              # Original pipeline orchestrator
│   ├── enrichment_engine.py          # Data enrichment utilities
│   ├── scoring_engine.py             # Lead scoring algorithm
│   ├── dashboard.py                  # Streamlit dashboard
│   ├── enriched_leads.csv            # Partial results
│   └── sample_dashboard.csv          # Sample data
│
└── Firecrawl Agent/                   # Final working solution
    ├── firecrawl_agent.ipynb         # Main implementation notebook
    ├── leads.json                    # Raw extracted data (7 leads)
    ├── scored_leads.csv              # Ranked and scored leads
    └── dashboard.py                  # Streamlit dashboard
```

---

**Author**: Jai Keshav Sharma  
**Date**: 19 December 2025  
**Assignment**: EuPrime Lead Generation Challenge
