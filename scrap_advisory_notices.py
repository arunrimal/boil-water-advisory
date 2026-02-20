"""
Phase 1: Collect all Boil Water Advisory/Order URLs from KDHE website
Author: Arun Rimal
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime

def scrape_bwa_urls(base_url="https://www.kdhe.ks.gov/CivicAlerts.aspx?CID=29"):
    """
    Scrapes all boil water advisory/order URLs from the KDHE landing page
    
    Returns:
        list: List of dictionaries containing URL and basic metadata
    """
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting URL collection...")
    print(f"Target URL: {base_url}\n")
    
    # Add headers to mimic a browser request
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        # Fetch the main page
        print("Fetching landing page...")
        response = requests.get(base_url, headers=headers, timeout=30)
        response.raise_for_status()
        
        print(f" Page loaded successfully (Status: {response.status_code})\n")
        
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        # print("this is soup: ",soup)
        
        # Find all boil water advisory/order links
        urls_collected = []

        # Method 1: Look for links in CivicAlerts structure
        alert_post = soup.find_all('div', class_='col-sm-8 col-md-9 d-flex flex-column justify-content-between')
        print(f"Found alert_post: {len(alert_post)}\n")

        for link in alert_post:
            # Find anchor tags within each div
            anchor = link.find('a', href=True)
            if anchor:
                href = anchor.get('href', '')
                
                # Build full URL
                if href.startswith('/'):
                    full_url = f"https://www.kdhe.ks.gov{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    full_url = f"https://www.kdhe.ks.gov/{href}"
                
                # Extract paragraph text
                paragraph = link.find('p', class_='mb-0')
                paragraph_text = paragraph.get_text(strip=True) if paragraph else ""
                confined_paragraph = paragraph_text.split('For consumer questions,')[0] if 'For consumer questions,' in paragraph_text else paragraph_text
                
                # Extract any visible text/title
                title = anchor.get_text(strip=True)  # Get text from anchor, not the whole div
                
                # Extract posted date from footer
                posted_on = None
                footer_post = link.find('div', class_='article-list-footer mt-auto')  # find on 'link', not 'alert_post'
                
                if footer_post:
                    # Get all divs within footer
                    footer_divs = footer_post.find_all('div')
                    if len(footer_divs) >= 2:
                        posted_on = footer_divs[1].get_text(strip=True)
                    # Alternatively, if it's always the second div:
                    # posted_on = footer_post.find_all('div')[1].get_text(strip=True) if len(footer_post.find_all('div')) >= 2 else None
                
                urls_collected.append({
                    'url': full_url,
                    'title': title,
                    'paragraph': confined_paragraph,
                    'posted_on': posted_on,
                    'scraped_at': datetime.now().isoformat()
                })
            
        # Remove duplicates based on URL
        unique_urls = []
        seen_urls = set()
        
        for item in urls_collected:
            if item['url'] not in seen_urls:
                seen_urls.add(item['url'])
                unique_urls.append(item)
        
        print(f"{'='*60}")
        print(f"COLLECTION SUMMARY")
        print(f"{'='*60}")
        print(f"Total links found: {len(urls_collected)}")
        print(f"Unique URLs: {len(unique_urls)}")
        print(f"{'='*60}\n")
        
        # Display first few URLs as preview
        if unique_urls:
            print("Preview of collected URLs:")
            for i, item in enumerate(unique_urls[:5], 1):
                print(f"{i}. {item['title'][:60]}...")
                print(f"   URL: {item['url']}")
                print(f"   ID: {item['posted_on']}\n")
            
            if len(unique_urls) > 5:
                print(f"... and {len(unique_urls) - 5} more URLs\n")
        
        return unique_urls
        
    except requests.RequestException as e:
        print(f" Error fetching page: {e}")
        return []
    except Exception as e:
        print(f" Error parsing page: {e}")
        return []


def save_urls_to_files(urls, json_file='bwa_urls.json', txt_file='bwa_urls.txt'):
    """
    Save collected URLs to both JSON and TXT files
    
    Args:
        urls: List of URL dictionaries
        json_file: Output JSON filename
        txt_file: Output TXT filename (simple list)
    """
    if not urls:
        print("No URLs to save!")
        return
    
    # Save as JSON (with metadata)
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(urls, f, indent=2, ensure_ascii=False)
    print(f" Saved detailed data to: {json_file}")
    
    # Save as simple text list (just URLs)
    with open(txt_file, 'w', encoding='utf-8') as f:
        for item in urls:
            f.write(f"{item['url']}\n")
    print(f" Saved URL list to: {txt_file}")
    
    print(f"\nTotal URLs saved: {len(urls)}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("KDHE BOIL WATER ADVISORY - URL COLLECTOR")
    print("Phase 1: Collecting all notice URLs")
    print("="*60 + "\n")
    
    base_url = "https://www.kdhe.ks.gov/m/newsflash/Home/Items?cat=29&page={}&sortBy=Category"

    # Scrape URLs
    for i in range(0, 8):  # Adjust range for more pages if needed
        print(f"\n--- Scraping page {i+1} ---\n")
        page_url = base_url.format(i)
        url_list = scrape_bwa_urls(page_url)
        
        # Save to files
        if url_list:
            save_urls_to_files(url_list, json_file=f'bwa_urls_page_{i+1}.json', txt_file=f'bwa_urls_page_{i+1}.txt')
        else:
            print(" No URLs collected on this page. Please check the website structure.")
        
        time.sleep(2)  # sleep time to avoid overwhelming the server
    url_list = scrape_bwa_urls()
    
    # Save to files
    if url_list:
        save_urls_to_files(url_list)
        print("\n Phase 1 Complete! Website URLs collected and saved successfully.")
    else:
        print("\n No URLs collected. Please check the website structure.")
    
    print("\n" + "="*60 + "\n")