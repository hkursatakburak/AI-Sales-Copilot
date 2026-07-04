import asyncio
import logging
from typing import List
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ai_sales_copilot")

app = FastAPI(
    title="AI Sales Copilot API",
    description="Asynchronous backend skeleton for AI Sales Copilot Chrome Extension",
    version="1.0.0",
)

# CORS Middleware configuration
# Allowed to all origins (*) for Chrome extension integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# Pydantic Models (Schemas)
# ==========================================

class AnalyzeRequest(BaseModel):
    """
    Request model for the analysis endpoint.
    """
    target_url: str = Field(
        ..., 
        description="The URL of the company to be analyzed.",
        examples=["https://example.com"]
    )
    user_context: str = Field(
        default="", 
        description="User context or product information to tailor the analysis.",
        examples=["Our product is an AI-powered automated testing tool."]
    )


class AnalyzeResponse(BaseModel):
    """
    Response model containing target company analysis and generated outreach draft.
    """
    company_summary: str = Field(
        ..., 
        description="Summary of the targeted company based on scraped data."
    )
    pain_points: List[str] = Field(
        ..., 
        description="Identified potential pain points of the targeted company."
    )
    cold_email: str = Field(
        ..., 
        description="Tailored cold outreach email template."
    )
    lead_score: int = Field(
        ..., 
        description="Calculated lead quality score from 0 to 100.",
        ge=0,
        le=100
    )


# ==========================================
# Mock Services (Scraper & LLM Integration)
# ==========================================

async def mock_scrape_website(url: str) -> str:
    """
    Asynchronously simulates web scraping of a target URL.
    In production, this will be replaced by a real scraper function.
    """
    logger.info(f"Starting mock scraping for URL: {url}")
    # Simulate network latency of scraping the website
    await asyncio.sleep(1.5)
    
    logger.info(f"Mock scraping completed for URL: {url}")
    # Return a simulated scraped raw text
    return (
        f"Mock Scraped Content for {url}:\n"
        "We are Acme Corp, a leading provider of enterprise cloud infrastructure and SaaS database solutions. "
        "We help thousands of companies manage their high-volume database queries and scale globally. "
        "Currently struggling with slow release cycles and manual testing bottlenecks for our cloud database services."
    )


async def mock_generate_ai_analysis(scraped_text: str, user_context: str) -> dict:
    """
    Asynchronously simulates AI analysis of scraped content using Gemini API.
    In production, this will be replaced by a real LLM generation function.
    """
    logger.info("Starting mock AI analysis")
    # Simulate LLM generation latency
    await asyncio.sleep(2.0)
    
    # Analyze and adjust response based on user context
    context_prefix = f"tailored to '{user_context}'" if user_context else "general outreach"
    logger.info(f"Mock AI analysis finished with context: {context_prefix}")
    
    # Generate realistic dummy response
    company_summary = (
        "Acme Corp is an enterprise-scale cloud infrastructure provider specializing in SaaS database solutions. "
        "They have a large global footprint but are currently facing scaling pains and developer velocity limits."
    )
    
    pain_points = [
        "Slow software release cycles due to database bottleneck challenges.",
        "Manual testing bottlenecks preventing rapid deployment of new features.",
        "Scaling infrastructure globally while keeping operational costs optimized."
    ]
    
    # A realistic tailored outreach email mockup
    cold_email = (
        "Subject: Accelerating Acme Corp's database release cycles\n\n"
        "Hi Acme Corp Team,\n\n"
        "I noticed that Acme Corp is doing incredible work scaling SaaS database solutions globally. "
        "However, as databases scale, release speed and manual testing verification can often become major bottlenecks.\n\n"
    )
    
    if user_context:
        cold_email += (
            f"Given your focus on '{user_context}', our solution can directly address these release bottlenecks "
            "by automating verification tests, helping your engineers ship database updates 3x faster.\n\n"
        )
    else:
        cold_email += (
            "We help enterprise cloud providers automate their release verification pipelines, "
            "allowing engineering teams to ship updates faster with 100% confidence.\n\n"
        )
        
    cold_email += (
        "Would you be open to a brief 10-minute call next Tuesday to discuss how we can help speed up your release cycles?\n\n"
        "Best regards,\n"
        "Sales Copilot Assistant"
    )
    
    lead_score = 85 if user_context else 60
    
    return {
        "company_summary": company_summary,
        "pain_points": pain_points,
        "cold_email": cold_email,
        "lead_score": lead_score
    }


# ==========================================
# API Endpoints
# ==========================================

@app.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Simple health check endpoint to verify backend status.
    """
    logger.info("Health check endpoint called")
    return {
        "status": "ok",
        "message": "AI Sales Copilot API is running successfully",
        "version": "1.0.0"
    }


@app.post("/api/v1/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def analyze_lead(request: AnalyzeRequest):
    """
    Main analysis endpoint.
    Receives target URL and context, scrapes the target page,
    generates analysis & cold email template, and returns structured data.
    """
    logger.info(f"Received analysis request for URL: {request.target_url}")
    
    try:
        # Step 1: Scrape target website asynchronously
        scraped_text = await mock_scrape_website(request.target_url)
        
        # Step 2: Generate AI analysis asynchronously
        analysis_result = await mock_generate_ai_analysis(scraped_text, request.user_context)
        
        # Step 3: Map and return response model
        return AnalyzeResponse(
            company_summary=analysis_result["company_summary"],
            pain_points=analysis_result["pain_points"],
            cold_email=analysis_result["cold_email"],
            lead_score=analysis_result["lead_score"]
        )
        
    except Exception as e:
        logger.error(f"Error during lead analysis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while analyzing the lead: {str(e)}"
        )
