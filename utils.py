import os
import requests
import asyncio
from io import BytesIO
from bs4 import BeautifulSoup
import time
# from PyPDF2 import PdfReader
# from playwright.async_api import async_playwright

def get_data_from_url(url: str) -> str:
    """
    Synchronous web scraping using requests and BeautifulSoup
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Add a small delay to be respectful to servers
        time.sleep(1)
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Get text content
        text = soup.get_text()
        
        # Clean up the text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
        
    except Exception as e:
        return f"Error scraping URL {url}: {str(e)}"

# Keep the async version for backward compatibility if needed
async def get_data_from_url_async(url: str) -> str:
    """
    Async version using Playwright (for standalone scripts)
    """
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until='networkidle')
        result = await page.evaluate("() => document.body.innerText")
        await browser.close()
        return result