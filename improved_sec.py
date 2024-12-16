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
                'file_path', 'form_file_name', 'filed', 'reporting_for', 
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

    def _extract_document_metadata(self, page, document_link, index: int) -> Dict:
        """Extract metadata with improved error handling and retry logic."""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                return {
                    "file_name": document_link.get_attribute('data-file-name'),
                    "file_number": page.locator("td.file-num a").nth(index).text_content(timeout=5000).strip(),
                    "form_file_name": page.locator("td.filetype a").nth(index).text_content(timeout=5000).strip(),
                    "incorporate": page.locator("td.incorporated").nth(index).text_content(timeout=5000).strip(),
                    "filed": page.locator("td.filed").nth(index).text_content(timeout=5000).strip(),
                    "end_date": page.locator("td.enddate").nth(index).text_content(timeout=5000).strip(),
                    "entity_name": page.locator("td.entity-name").nth(index).text_content(timeout=5000).strip(),
                    "location": page.locator("td.biz-location.located").nth(index).text_content(timeout=5000).strip(),
                    "film_number": page.locator("td.film-num").nth(index).text_content(timeout=5000).strip(),
                    "cik_number": page.locator("td.cik").nth(index).text_content(timeout=5000).strip(),
                }
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to extract metadata after {max_retries} attempts: {e}")
                time.sleep(1)
        raise Exception("Failed to extract metadata")

    def scrape_document(self, page, url_type: str, document_link, details: Dict) -> Optional[str]:
        doc_dir = self.output_dir / url_type
        doc_dir.mkdir(exist_ok=True)
        
        pdf_path = doc_dir / f"{details['form_file_name']}_{details['file_number']}_{details['film_number']}.pdf"
        
        if pdf_path.exists():
            logging.info(f"Document already exists: {pdf_path}")
            return str(pdf_path)

        try:
            document_link.click(timeout=5000)
            
            with page.expect_popup(timeout=30000) as popup_info:
                if not self._safe_wait_and_click(page, "button.btn.btn-warning:has-text('Open document')", timeout=10000):
                    return None
                
                self._safe_wait_and_click(page, "#close-modal", timeout=5000)

            document_page = popup_info.value
            document_page.wait_for_load_state("domcontentloaded", timeout=30000)
            
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    document_page.pdf(path=str(pdf_path))
                    document_page.close()
                    logging.info(f"Successfully saved document to {pdf_path}")
                    return str(pdf_path)
                except Exception as e:
                    if attempt == max_retries - 1:
                        document_page.close()
                        raise
                    logging.warning(f"PDF save attempt {attempt + 1} failed: {e}")
                    time.sleep(2)
            
        except Exception as e:
            logging.error(f"Failed to process document {details.get('file_name', 'unknown')}: {e}")
            return None

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
                    pdf_path = self.scrape_document(page, url_type, doc_link, details)
                    
                    if pdf_path:
                        self._write_csv_row([
                            pdf_path, url_type, details["filed"], details["end_date"],
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
        # '10-Q': [
        #     "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=10-Q",
        #     "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=10-Q",
        #     "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=10-Q",
        # ],
        # '10-K': [
        #     "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=10-K",
        #     "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=10-K",
        #     "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=10-K",
        # ],
        '8-K': [
            "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=8-K",
            # "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=8-K",
            # "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=8-K",
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