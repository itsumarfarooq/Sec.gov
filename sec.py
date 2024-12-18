from playwright.sync_api import sync_playwright
import csv
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sec_scraper.log'),
        logging.StreamHandler()
    ]
)

class SECDocumentScraper:
    def __init__(self, output_dir: str = "sec_gov", csv_file: str = 'Master_file.csv', timeout: int = 30000):
        self.output_dir = Path(output_dir)
        self.csv_file = Path(csv_file)
        self.timeout = timeout
        self.setup_directories()
        
    def setup_directories(self) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self._initialize_csv()
        except Exception as e:
            logging.error(f"Failed to setup directories: {e}")
            raise

    def _initialize_csv(self) -> None:
        if not self.csv_file.exists():
            headers = [
                'file_url', 'form_file_name', 'filed', 'reporting_for', 
                'filing_entity_person', 'cik', 'located', 'incorporated', 
                'file_number', 'firm_number', 'form_type'
            ]
            self._write_csv_row(headers, mode='w')

    def _write_csv_row(self, row: List[str], mode: str = 'a') -> None:
        try:
            with open(self.csv_file, mode=mode, newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(row)
        except Exception as e:
            logging.error(f"Failed to write to CSV: {e}")

    def _safe_wait_and_click(self, page, selector: str, timeout: int = 5000) -> bool:
        try:
            element = page.wait_for_selector(selector, timeout=timeout)
            if element and element.is_visible():
                element.click(force=True)
                return True
        except Exception as e:
            logging.warning(f"Failed to find or click element {selector}: {e}")
            return False
        return False

    def ensure_checkboxes_checked(self, page) -> None:
        selectors = [
            "input#col-cik", "input#col-located", "input#col-incorporated",
            "input#col-file-num", "input#col-film-num", "input#col-filed"
        ]
        
        for selector in selectors:
            try:
                checkbox = page.wait_for_selector(selector, timeout=5000)
                if checkbox and checkbox.is_visible() and not checkbox.is_checked():
                    checkbox.click(force=True)
                    time.sleep(0.5)
            except Exception as e:
                logging.warning(f"Checkbox {selector} not found or not clickable: {e}")

    # def _extract_document_metadata(self, page, doc_link=None, row_index=None) -> Dict:
    #     """Extract metadata for a single document row, merging multiple file and film numbers."""
    #     try:
    #         # Fetch all matching elements for file numbers and film numbers
    #         file_number_elements = page.locator(f"tr:nth-child({row_index + 1}) td.file-num a").all()
    #         film_number_elements = page.locator(f"tr:nth-child({row_index + 1}) td.film-num").all()

    #         # Combine multiple file numbers and film numbers into a single string
    #         file_numbers = " ".join(el.text_content().strip() for el in file_number_elements)
    #         film_numbers = " ".join(el.text_content().strip() for el in film_number_elements)

    #         # Extract other metadata
    #         row_data = {
    #             "file_name": doc_link.get_attribute('data-file-name'),
    #             "file_number": file_numbers,
    #             "film_number": film_numbers,
    #             "form_file_name": page.locator(f"tr:nth-child({row_index + 1}) td.filetype a").text_content().strip(),
    #             "incorporate": page.locator(f"tr:nth-child({row_index + 1}) td.incorporated").text_content().strip(),
    #             "filed": page.locator(f"tr:nth-child({row_index + 1}) td.filed").text_content().strip(),
    #             "end_date": page.locator(f"tr:nth-child({row_index + 1}) td.enddate").text_content().strip(),
    #             "entity_name": page.locator(f"tr:nth-child({row_index + 1}) td.entity-name").text_content().strip(),
    #             "location": page.locator(f"tr:nth-child({row_index + 1}) td.biz-location.located").text_content().strip(),
    #             "cik_number": page.locator(f"tr:nth-child({row_index + 1}) td.cik").text_content().strip(),
    #         }
    #         return row_data
    #     except Exception as e:
    #         logging.error(f"Failed to extract metadata for row {row_index}: {e}")
    #         return {}
    def _extract_document_metadata(self, page, doc_link=None, row_index=None) -> Dict:
        """Extract metadata for a single document row, merging multiple file and film numbers."""
        try:
            # Fetch all matching elements for file numbers
            file_number_elements = page.locator(f"tr:nth-child({row_index + 1}) td.file-num a").all()
            file_numbers = " ".join(el.text_content().strip() for el in file_number_elements)

            # Handle film numbers, replacing <br> with space if present
            film_number_element = page.locator(f"tr:nth-child({row_index + 1}) td.film-num")
            if film_number_element:
                # Get the inner HTML and replace <br> with a space
                film_number_html = film_number_element.inner_html()
                film_numbers = film_number_html.replace("<br>", " ").strip()
            else:
                film_numbers = ""

            # Handle incorporated field, replacing <br> with space if present
            incorporated_element = page.locator(f"tr:nth-child({row_index + 1}) td.incorporated")
            if incorporated_element:
                incorporated_html = incorporated_element.inner_html()
                incorporated = incorporated_html.replace("<br>", " ").strip()
            else:
                incorporated = ""

            # Handle located field, replacing <br> with space if present
            located_element = page.locator(f"tr:nth-child({row_index + 1}) td.biz-location.located")
            if located_element:
                located_html = located_element.inner_html()
                located = located_html.replace("<br>", " ").strip()
            else:
                located = ""

            # Extract other metadata
            row_data = {
                "file_name": doc_link.get_attribute('data-file-name') if doc_link else None,
                "file_number": file_numbers,
                "film_number": film_numbers,
                "form_file_name": page.locator(f"tr:nth-child({row_index + 1}) td.filetype a").text_content().strip(),
                "incorporate": incorporated,  # Store the processed incorporated value here
                "location": located,  # Store the processed located value here
                "filed": page.locator(f"tr:nth-child({row_index + 1}) td.filed").text_content().strip(),
                "end_date": page.locator(f"tr:nth-child({row_index + 1}) td.enddate").text_content().strip(),
                "entity_name": page.locator(f"tr:nth-child({row_index + 1}) td.entity-name").text_content().strip(),
                "cik_number": page.locator(f"tr:nth-child({row_index + 1}) td.cik").text_content().strip(),
            }
            return row_data
        except Exception as e:
            logging.error(f"Failed to extract metadata for row {row_index}: {e}")
            return {}






    def scrape_document(self, page, url_type: str, document_link, details: Dict) -> Optional[str]:
        sanitized_url_type = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in url_type.strip())
        
        try:
            document_link.click(timeout=5000)
            open_file_selector = "a#open-file"
            open_file_element = page.wait_for_selector(open_file_selector, timeout=10000)
            if open_file_element:
                file_url = open_file_element.get_attribute("href")
                logging.info(f"Document URL captured: {file_url}")
                self._safe_wait_and_click(page, "#close-modal", timeout=5000)
                return file_url
            else:
                logging.warning("Open document link not found")
                return None

        except Exception as e:
            logging.warning(f"Failed to extract document URL: {e}")   
            return None
                # if attempt == max_retries - 1:
                #     return None
                # logging.warning(f"Retrying after 15 minutes...")
                # time.sleep(15 * 60)  # Wait for 15 minutes before retrying



    def get_document_details(self, page, url_type: str) -> None:
        self.ensure_checkboxes_checked(page)
        
        try:
            link_selector = "a.preview-file[data-file-name]"
            page.wait_for_selector(link_selector, timeout=10000)
            document_links = page.locator(link_selector).all()
            
            logging.info(f"Found {len(document_links)} documents on current page")
            
            for i, doc_link in enumerate(document_links):
                try:
                    details = self._extract_document_metadata(page, doc_link, i)
                    file_url = self.scrape_document(page, url_type, doc_link, details)
                    
                    if file_url:
                        self._write_csv_row([
                            file_url, url_type, details["filed"], details["end_date"],
                            details["entity_name"], details["cik_number"], details["location"],
                            details["incorporate"], details["file_number"], details["film_number"],
                            details["form_file_name"]
                        ])
                    time.sleep(1)  # Add small delay between documents
                except Exception as e:
                    logging.error(f"Failed to process document {i}: {e}")
                    continue
                    
        except Exception as e:
            logging.error(f"Failed to process page: {e}")

def main():
    url_groups = {
        '8-K': [
           "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=8-K",
           "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=8-K",
           "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=8-K",
        ],
        '10-Q': [
            "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=10-Q",
            "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=10-Q",
            "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=10-Q",
        ],
        '10-K': [
           "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=10-K",
           "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=10-K",
           "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=10-K",
        ]
        
    }

    scraper = SECDocumentScraper()
    
    with sync_playwright() as p:
        for url_type, urls in url_groups.items():
            logging.info(f"Processing {url_type} URLs")
            
            for url in urls:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context(viewport={'width': 1920, 'height': 1080})
                page = context.new_page()
                page_number = 1
                
                
                
                while True:
                    paginated_url = f"{url}&page={page_number}"
                    logging.info(f"Processing page {page_number}: {paginated_url}")
                    
                    try:
                        page.goto(paginated_url, wait_until="domcontentloaded", timeout=60000)
                        time.sleep(10)  # Allow page to stabilize
                        
                        if not page.locator('th#filetype.filetype[style=""]:has-text("Form & File")').is_visible():
                            logging.info("Please wait for 10 minutes checking for request limit...")
                            time.sleep(12 * 60) #wait until traffic limit unblocks
                            page.goto(paginated_url, wait_until="domcontentloaded", timeout=60000)
                            time.sleep(10)
                            if not page.locator('th#filetype.filetype[style=""]:has-text("Form & File")').is_visible():
                                logging.info("No more results found")
                                break
                            
                        
                        scraper.get_document_details(page, url_type)
                        page_number += 1
                        
                    except Exception as e:
                        logging.error(f"Failed to process {paginated_url}: {e}")
                        break
                    
                    finally:
                        time.sleep(5)  # Add delay between pages
                
                try:
                    page.close()
                    context.close()
                    browser.close()
                except Exception as e:
                    logging.error(f"Error closing browser resources: {e}")
            
            logging.info(f"Completed processing {url_type} URLs")
        
        logging.info("All URLs processed")

if __name__ == "__main__":
    main()
