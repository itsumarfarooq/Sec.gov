from playwright.sync_api import sync_playwright
import os
import csv

def write_csv_headers(file_path):
    if not os.path.exists(file_path):
        with open(file_path, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'file_path', 'form_file_name', 'filed', 'reporting_for', 'filing_entity_person', 'cik', 
                'located', 'incorporated', 'file_number', 'film_number'
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
    
    for selector in selectors:
        page.wait_for_selector(selector)
        checkbox = page.locator(selector)
        checkbox.scroll_into_view_if_needed()
        if not checkbox.is_checked():
            checkbox.click(force=True)

    page.wait_for_timeout(2000)

def scrape_documents(page, csv_file_path, url_type):
    """Scrape documents on the current page after ensuring checkboxes are clicked."""
    check_checkboxes(page)
    
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    link_selector = "a.preview-file[data-file-name]"
    page.wait_for_selector(link_selector)

    document_links = page.locator(link_selector)
    document_count = document_links.count()

    print(f"Number of document links found: {document_count}")

    for i in range(document_count):
        document_link = document_links.nth(i)
        file_name = document_link.get_attribute('data-file-name')
        file_number_selector = "td.file-num a"
        file_number = page.locator(file_number_selector).nth(i).text_content().strip()
        incorporate_selector = "td.incorporated"
        incorporate = page.locator(incorporate_selector).nth(i).text_content().strip()
        adsh = document_link.get_attribute('data-adsh')
        date_selector = "td.enddate"
        entity_selector = "td.entity-name"
        location_selector = "td.biz-location.located"
        filed_selector = f"input#col-filed:nth-of-type({i+1})" 
        filed_selector = "td.filed"
        filed = page.locator(filed_selector).nth(i).text_content().strip()     
        end_date = page.locator(date_selector).nth(i).text_content().strip()
        entity_name = page.locator(entity_selector).nth(i).text_content().strip()
        location = page.locator(location_selector).nth(i).text_content().strip()
        film_number_selector = "td.film-num"
        film_number = page.locator(film_number_selector).nth(i).text_content().strip()
        cik_number_selector = "td.cik"
        cik_number = page.locator(cik_number_selector).nth(i).text_content().strip()
        
        
        directory_name = url_type
        directory_path = os.path.join("sec_gov", directory_name)
        os.makedirs(directory_path, exist_ok=True)
        
        print(f"Processing document: {file_name} (ADSH: {adsh}, Film Number: {film_number})")

        document_link.click()
        print(f"Clicked the link for {file_name}")

        with page.expect_popup(timeout=60000) as popup_info:
            button_selector = "button.btn.btn-warning:has-text('Open document')"
            page.wait_for_selector(button_selector)
            button = page.locator(button_selector)
            button.click()
            print(f"Clicked the 'Open document' button for {file_name} successfully!")
            try:
                close_button_selector = "#close-modal"
                page.locator(close_button_selector).click()
            except Exception as e:
                print(f"No modal found or failed to close modal: {e}")
        
        document_page = popup_info.value
        document_page.wait_for_load_state("domcontentloaded", timeout=30000)
        document_page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        
        pdf_path = os.path.join(directory_path, f"{file_number}_{film_number}.pdf")
        document_page.pdf(path=pdf_path)
        print(f"Document saved as {pdf_path}")
        document_page.close()
        print(f"Closed the document tab for {file_name}")
        file_txt_name = url_type
        write_to_csv(csv_file_path, pdf_path, file_txt_name, filed, end_date, entity_name, cik_number, location, incorporate, file_number, film_number)

def scrape_url(page, url, csv_file_path, url_type):
    """Scrape a specific URL, iterating through its pages."""
    page_number = 1 
    while page_number <= 10:
        paginated_url = f"{url}&page={page_number}"
        print(f"Scraping page {page_number} of URL: {paginated_url}")
        try:
            page.goto(paginated_url, wait_until="domcontentloaded", timeout=60000)
            check_checkboxes(page) 
            scrape_documents(page, csv_file_path, url_type)
            
            next_button_selector = "a.page-link[data-value='nextPage']"
            next_button = page.locator(next_button_selector)
            if next_button and next_button.is_visible() and next_button.is_enabled():
                page_number += 1
            else:
                print("No more pages to navigate. Exiting loop.")
                break
            
        except Exception as e:
            print(f"Failed to scrape page {page_number} of URL: {paginated_url}. Error: {e}")
            break

def click_checkboxes_on_all_urls():
    """Scrape all URLs, visiting pages for each URL."""
    csv_file_path = 'scraped_documents.csv'
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

