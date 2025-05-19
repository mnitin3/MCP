import arxiv
import json
import os
from typing import List
from mcp.server.fastmcp import FastMCP
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

PAPER_DIR = "papers"

# Initialize FastMCP server
mcp = FastMCP("research")

@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    
    Args:
        topic: The topic to search for
        max_results: Maximum number of results to retrieve (default: 5)
        
    Returns:
        List of paper IDs found in the search
    """
    
    # Use arxiv to find the papers 
    client = arxiv.Client()

    # Search for the most relevant articles matching the queried topic
    search = arxiv.Search(
        query = topic,
        max_results = max_results,
        sort_by = arxiv.SortCriterion.Relevance
    )

    papers = client.results(search)
    
    # Create directory for this topic
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    
    file_path = os.path.join(path, "papers_info.json")

    # Try to load existing papers info
    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        papers_info = {}

    # Process each paper and add to papers_info  
    paper_ids = []
    for paper in papers:
        paper_ids.append(paper.get_short_id())
        paper_info = {
            'title': paper.title,
            'authors': [author.name for author in paper.authors],
            'summary': paper.summary,
            'pdf_url': paper.pdf_url,
            'published': str(paper.published.date())
        }
        papers_info[paper.get_short_id()] = paper_info
    
    # Save updated papers_info to json file
    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)
    
    print(f"Results are saved in: {file_path}")
    
    return paper_ids

@mcp.tool()
def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.
    
    Args:
        paper_id: The ID of the paper to look for
        
    Returns:
        JSON string with paper information if found, error message if not found
    """
 
    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, "papers_info.json")
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    print(f"Error reading {file_path}: {str(e)}")
                    continue
    
    return f"There's no saved information related to paper {paper_id}."

@mcp.tool()
def get_stock_data(ticker: str, period: str = "6mo", interval: str = "1d") -> dict:
    """
    Fetch stock data for a given ticker using yfinance.

    Args:
    ----------
    ticker : str
        Stock symbol (e.g., "AAPL", "MSFT").
    period : str
        Period to fetch (e.g., "1mo", "3mo", "6mo", "1y", "5y", "max").
    interval : str
        Data interval (e.g., "1d", "1h", "1wk").

    Returns:
    -------
    dict
        Dictionary containing historical data, current price, and basic stats.
    """
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period, interval=interval)
        info = stock.info

        current_price = info.get("regularMarketPrice", None)
        previous_close = info.get("previousClose", None)
        market_cap = info.get("marketCap", None)
        pe_ratio = info.get("trailingPE", None)
        eps = info.get("trailingEps", None)
        dividend_yield = info.get("dividendYield", None)

        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "current_price": current_price,
            "previous_close": previous_close,
            "market_cap": market_cap,
            "pe_ratio": pe_ratio,
            "eps": eps,
            "dividend_yield": dividend_yield,
            "historical_data": hist.reset_index().to_dict(orient="records")
        }

    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')