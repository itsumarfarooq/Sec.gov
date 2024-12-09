from playwright.sync_api import sync_playwright
import os
import csv

def write_csv_headers(file_path):
    if not os.path.exists(file_path):
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'file_path', 'form_file_name', 'filed', 'reporting_for', 'filing_entity_person', 'cik', 
                'located', 'incorporated', 'file_number', 'firm_number'
            ])

def write_to_csv(file_path, form_file_name, filed, reporting_for, entity_name, cik, located, incorporated, file_number, film_number, pdf_path):
    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow([form_file_name, filed, reporting_for, entity_name, cik, located, incorporated, file_number, film_number, pdf_path])

def check_checkboxes(page):
    """Ensure the checkboxes are clicked and checked on the current page."""
    
    selectors = ["input#col-cik", "input#col-located",
                "input#col-incorporated", "input#col-file-num",
                "input#col-film-num", "input#col-filed"]
    try:
        for selector in selectors:
            page.wait_for_selector(selector)
            checkbox = page.locator(selector)
            if checkbox.is_visible():
                checkbox.scroll_into_view_if_needed()
                if not checkbox.is_checked():
                    checkbox.click(force=True)
    except Exception as e:
        print(f"Error processing checkbox {selector}: {e}")

    page.wait_for_timeout(2000)

def _get_document_details(page, csv_file_path, url_type):
    document_record = 0
    """Scrape documents on the current page after ensuring checkboxes are clicked."""
    check_checkboxes(page)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    link_selector = "a.preview-file[data-file-name]"
    page.wait_for_selector(link_selector)

    document_links = page.locator(link_selector)
    document_count = document_links.count()

    print(f"Number of document links found: {document_count}")

    for i in range(document_count):
        # Extract metadata for each document
        document_link = document_links.nth(i)
        details = {
            "file_name": document_link.get_attribute('data-file-name'),
            "adsh": document_link.get_attribute('data-adsh'),
            "file_number": page.locator("td.file-num a").nth(i).text_content().strip(),
            "incorporate": page.locator("td.incorporated").nth(i).text_content().strip(),
            "filed": page.locator("td.filed").nth(i).text_content().strip(),
            "end_date": page.locator("td.enddate").nth(i).text_content().strip(),
            "entity_name": page.locator("td.entity-name").nth(i).text_content().strip(),
            "location": page.locator("td.biz-location.located").nth(i).text_content().strip(),
            "film_number": page.locator("td.film-num").nth(i).text_content().strip(),
            "cik_number": page.locator("td.cik").nth(i).text_content().strip(),
        }

        # Process the document
        pdf_path = scrape_document(page, url_type, document_link, details)

        # Save metadata to CSV
        write_to_csv(
            csv_file_path, 
            pdf_path, url_type, details["filed"], details["end_date"],
            details["entity_name"], details["cik_number"], details["location"],
            details["incorporate"], details["file_number"], details["film_number"]
        )
    
def scrape_document(page, url_type, document_link, details):
    """Process and save a single document."""
    directory_path = os.path.join("sec_gov", url_type)
    os.makedirs(directory_path, exist_ok=True)

    pdf_path = os.path.join(directory_path, f"{details['file_number']}_{details['film_number']}.pdf")
    print(f"Processing document: {details['file_name']} (ADSH: {details['adsh']}, Film Number: {details['film_number']})")
    document_link.click()
    print(f"Clicked the link for {details['file_name']}")

    with page.expect_popup(timeout=60000) as popup_info:
        button_selector = "button.btn.btn-warning:has-text('Open document')"
        page.wait_for_selector(button_selector)
        page.locator(button_selector).click()
        print(f"Clicked the 'Open document' button for {details['file_name']} successfully!")
        try:
            page.locator("#close-modal").click()
        except Exception as e:
            print(f"No modal found or failed to close modal: {e}")

#    page.wait_for_timeout(2000)
    document_page = popup_info.value
    document_page.wait_for_load_state("domcontentloaded", timeout=30000)
    document_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    document_page.pdf(path=pdf_path)
    print(f"Document saved as {pdf_path}")
#    page.wait_for_timeout(2000)
    document_page.close()

    return pdf_path
        

def scrape_url(page, url, csv_file_path, url_type):
    """Scrape a specific URL, iterating through its pages."""
    page_number = 1
    while page_number:
        paginated_url = f"{url}&page={page_number}"
        print(f"Scraping page {page_number} of URL: {paginated_url}")
        try:
            page.goto(paginated_url, wait_until="domcontentloaded", timeout=60000)
            print("Please wait for 10 seconds next page is loading!")
            page.wait_for_timeout(10000) 
            #TO check if next the page is available or empty
            if not page.locator('th#filetype.filetype[style=""]:has-text("Form & File")').is_visible():
                print("No results found!. Moving to next url")
                break
            else:
                check_checkboxes(page) 
                _get_document_details(page, csv_file_path, url_type)
                page_number += 1
            
        except Exception as e:
            print(f"Failed to scrape page {page_number} of URL: {paginated_url}. Error: {e}")
            break

def click_checkboxes_on_all_urls():
    """Scrape all URLs, visiting pages for each URL."""
    csv_file_path = 'Master_file.csv'
    write_csv_headers(csv_file_path)
    directory_path = "sec_gov"
    try:
        os.makedirs(directory_path, exist_ok=True)
    except Exception as e:
        print(f"Error creating directory '{directory_path}': {e}")
    
    with sync_playwright() as p:
        url_groups = {
            '10-Q': [
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=10-Q",
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=10-Q",
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=10-Q",
            ],
            '10-K': [
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=10-K",
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=10-K",
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=10-K",
            ],
            '8-K': [
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2023-12-01&enddt=2024-12-01&filter_forms=8-K",
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2022-12-01&enddt=2023-12-01&filter_forms=8-K",
                "https://www.sec.gov/edgar/search/#/q=oil&dateRange=custom&startdt=2021-12-01&enddt=2022-12-01&filter_forms=8-K",
            ]
        }

        for url_type, urls in url_groups.items():
            print(f"Processing {url_type} URLs:")
            for url in urls:
               
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                scrape_url(page, url, csv_file_path, url_type) 
                browser.close()
            print(f"Completed processing {url_type} URLs.")
        print("All URLs processed.")

if __name__ == "__main__":
    click_checkboxes_on_all_urls()

