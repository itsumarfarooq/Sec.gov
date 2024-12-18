import csv
import os
import time
import logging
from playwright.sync_api import sync_playwright

# Setup logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()

# Define the headers for the CSV file
fieldnames = ['file_url', 'file_path', 'form_file_name', 'filed', 'reporting_for', 
              'filing_entity_person', 'cik', 'located', 'incorporated', 
              'file_number', 'firm_number', 'form_type']

# Function to initialize the CSV file with headers
def create_update_csv(output_csv_file):
    """Create the CSV file and write headers"""
    try:
        with open(output_csv_file, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            logger.info(f"Headers written to {output_csv_file}")
    except Exception as e:
        logger.error(f"Error creating CSV file: {e}")

# Function to download a PDF and save it to the correct location
def download_pdf(page, file_url, pdf_save_path, retry_count=3):
    """Download the PDF from the URL and save it, retrying in case of failure"""
    try:
        response = page.goto(file_url)
        logger.info(f"Request URL: {file_url} - Status Code: {response.status}")

        # Retry logic for status codes like 403 or other error codes
        while response.status in [403, 500, 503, 504] and retry_count > 0:
            logger.warning(f"Error {response.status} encountered. Retrying in 15 minutes...")
            time.sleep(15 * 60)  # Wait for 15 minutes
            page.reload()  # Refresh the page
            response = page.goto(file_url)
            retry_count -= 1

        if response.status == 200:
            page.wait_for_load_state("load")
            page.pdf(path=pdf_save_path, format='A4')  # Save PDF in A4 format
            logger.info(f"Saved PDF to {pdf_save_path}.")
            return True
        else:
            logger.error(f"Failed to load {file_url}: Status Code {response.status}")
            return False
    except Exception as e:
        logger.error(f"Error downloading PDF from {file_url}: {e}")
        return False

# Function to create the necessary directories for storing PDFs
def create_directories(form_file_name, parent_dir):
    """Create directories for storing PDFs based on the form_file_name"""
    directory_name = form_file_name.split(' ')[0]  # Get the first word (e.g., 8-K, 10-Q)
    form_type_dir = os.path.join(parent_dir, directory_name)
    os.makedirs(form_type_dir, exist_ok=True)  # Create directory if it doesn't exist
    return form_type_dir, directory_name

# Function to update the CSV file with the download result
def update_csv_file(output_csv_file, row):
    """Append updated row to the CSV file after PDF download"""
    try:
        with open(output_csv_file, mode='a', newline='', encoding='utf-8') as output_file:
            writer = csv.DictWriter(output_file, fieldnames=fieldnames)
            writer.writerow(row)
            logger.info(f"Updated record for {row['file_url']} in the CSV.")
    except Exception as e:
        logger.error(f"Error updating CSV file: {e}")

# Main function to process CSV file and download documents
def download_documents_from_csv(csv_file, output_csv_file):
    """Download documents from URLs and update the CSV file with the file path"""
    parent_dir = 'sec_gov'  # Root directory for the PDFs
    os.makedirs(parent_dir, exist_ok=True)  # Create the root directory if not exists

    try:
        with open(csv_file, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)  # Launch browser in non-headless mode
                context = browser.new_context()

                for row in reader:
                    file_url = row['file_url']
                    form_file_name = row['form_file_name']
                    form_type = row['form_type']
                    form_type_dir, directory_name = create_directories(form_file_name, parent_dir)

                    # Create a custom file name for saving the PDF with form_type included
                    custom_file_name = f"{form_type}_{form_file_name}_{row['file_number']}_{row['firm_number']}.pdf"
                    custom_file_name = custom_file_name.replace('/', '_').replace('\\', '_')  # Sanitize the file name
                    pdf_save_path = os.path.join(form_type_dir, custom_file_name)

                    # Try downloading the PDF
                    page = context.new_page()
                    if download_pdf(page, file_url, pdf_save_path):
                        row['file_path'] = pdf_save_path  # Update the row with the file path
                    else:
                        row['file_path'] = 'Failed to download'

                    # Update the CSV file immediately after download
                    update_csv_file(output_csv_file, row)

                    page.close()
                    time.sleep(2)  # Simulate a delay to avoid rate limiting

                browser.close()
        logger.info(f"Download process completed. Updated CSV saved to {output_csv_file}")
    
    except Exception as e:
        logger.error(f"Error processing CSV file: {e}")

# Main entry point
if __name__ == '__main__':
    # Define paths to input and output CSV files
    csv_file = 'Master_file.csv'  # Replace with your actual CSV file path
    output_csv_file = 'Updated_Master_file.csv'  # Desired output CSV file

    # Step 1: Create the update CSV file with headers
    create_update_csv(output_csv_file)

    # Step 2: Download documents and update the CSV file
    download_documents_from_csv(csv_file, output_csv_file)
