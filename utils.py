import pdfplumber
import re
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from io import BytesIO


def extract_master_data(master_pdf_path):
    """
    Extracts master account information and its subordinate accounts
    from the Master PDF. Returns a dictionary where the key is the
    Master Account (Name and Number) and the value is a list of
    subordinate accounts in order.
    """
    master_data = {}  # Dictionary to store the results
    current_master_account = None  # Keep track of the current Master Account

    with pdfplumber.open(master_pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            lines = text.splitlines()  # Split the page text into lines
            
            # Check if this page starts a new Master Account (Page 1 of X)
            if "Page 1 of" in lines[0]:
                # Extract the Master Account Name and Number
                for i, line in enumerate(lines):
                    if "Electric Summary Billing Statement for:" in line:
                        master_name = lines[i + 1].strip()  # Line under the key phrase
                        break

                for line in lines:
                    if line.startswith("Account Number:"):
                        master_number = line.replace("Account Number:", "").strip()
                        break

                # Define the key for the current master account
                current_master_account = f"{master_number} - {master_name}"
                master_data[current_master_account] = []  # Initialize the subordinate list

            # If we are within a Master Account, extract Subordinate Accounts
            if current_master_account:
                start_extracting = False  # Track when to start reading subordinate accounts

                for line in lines:
                    if "Account Number Name/ID Total" in line:
                        start_extracting = True
                        continue  # Skip this line

                    if start_extracting:
                        if "Final Bill Transfers" in line:
                            break  # Stop extracting when we hit this line

                        if " / " in line:  # Identify subordinate accounts
                            # Extract only the account numbers and reformat
                            parts = line.split(" / ")
                            if len(parts) >= 2:  # Ensure we have both parts
                                account_number = parts[0].strip()
                                subordinate_number = parts[1].split()[0].strip()  # Take only the first part
                                formatted_account = f"{account_number} - {subordinate_number}"
                                master_data[current_master_account].append(formatted_account)

    print("Extracted Master Data:")
    for master_account, subordinates in master_data.items():
        print(f"{master_account}:")
        for subordinate in subordinates:
            print(f"  {subordinate}")  # Print each subordinate account on a new line


    return master_data


def extract_subordinate_data(subordinate_pdf_path):
    """
    Extracts subordinate account information from the Subordinate PDF.
    Returns a dictionary where the key is the Subordinate account number
    and the value is a list of page numbers associated with that account.
    Blank pages (following the account info) will be included.
    """
    subordinate_data = {}  # Dictionary to store subordinate account number and associated pages
    current_account_number = None  # Keep track of the current subordinate account number
    current_pages = []  # List to track pages for the current subordinate account

    print(f"-------Staring Subordinate Page Analysis---------")
    
    with pdfplumber.open(subordinate_pdf_path) as pdf:
        # Iterate through all pages in the PDF
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            lines = text.splitlines()  # Split the page text into lines

            # Ensure the page has enough lines for checking "Page 1 of X"
            if len(lines) > 2 and "Page 1 of" in lines[2]:
                # Extract the account number from the 6th line (e.g., "26-DEC-2024 022222800 - 2200002 - 7 RIO RANCHO, NM")
                if len(lines) > 5:  # Make sure there are at least 6 lines on the page
                    account_line = lines[5]  # The account line is on the 6th line (index 5)
                    match = re.search(r'(\d{9}) - (\d{7})', account_line)  # Look for account number pattern

                    if match:
                        account_number = f"{match.group(1)} - {match.group(2)}"

                        # If we've encountered a new account and it's not the first page, store the previous account's data
                        if current_account_number and current_pages:
                            subordinate_data[current_account_number] = current_pages

                        # Start tracking the new account and its pages
                        current_account_number = account_number
                        print(f"Working On Account: {current_account_number}")
                        current_pages = [page_num]  # Initialize with the current page
                    else:
                        # If no account number found, skip this page
                        continue
            else:
                # Only add pages to the current account if it's already set
                if current_account_number:
                    current_pages.append(page_num)

        # After the loop, store the last account's data if it exists
        if current_account_number and current_pages:
            subordinate_data[current_account_number] = current_pages

    # Print extracted subordinate data for review
    print("Extracted Subordinate Data:")
    for account_number, pages in subordinate_data.items():
        print(f"Account: {account_number}")
        print(f"  Total Pages: {len(pages)}")  # Print the total number of pages for the account
        for page in pages:
            print(f"  Page {page}")
            
    # Create the "SubordinateTest.pdf" file from the gathered pages
    #with open(subordinate_pdf_path, 'rb') as infile, open('SubordinateTest.pdf', 'wb') as outfile:
    #    reader = PyPDF2.PdfReader(infile)
    #    writer = PyPDF2.PdfWriter()

        # Loop through the subordinate_data to extract pages
    #    for account_number, pages in subordinate_data.items():
    #        print(f"Creating PDF for account {account_number} with pages: {pages}")
    #        for page_num in pages:
                # PyPDF2 uses 0-based indexing for pages, so subtract 1
    #            writer.add_page(reader.pages[page_num - 1])

    #    # Write the collected pages to the new test PDF
    #    writer.write(outfile)

    #print("SubordinateTest.pdf has been created with the extracted pages.")
            

    return subordinate_data






def create_blank_page():
    """
    Creates a blank page using ReportLab and returns it as a BytesIO object.
    """
    packet = BytesIO()
    c = canvas.Canvas(packet)
    c.showPage()  # Create a blank page
    c.save()
    packet.seek(0)
    return packet

def reorder_and_merge(master_data, subordinate_data, subordinate_pdf_path, output_pdf_path):
    """
    Reorders and merges Subordinate PDF pages based on Master PDF structure.
    Adds a blank page if a subordinate account has an odd number of pages.
    Appends unprocessed subordinate accounts to the end.
    """
    writer = PdfWriter()
    processed_subordinates = set()  # To track processed subordinate accounts

    print(f"-------Starting PDF Creation and Reorder---------")
    
    # Open the Subordinate PDF
    with open(subordinate_pdf_path, 'rb') as f:
        reader = PdfReader(f)

        # Process subordinate accounts based on the Master Account structure
        for master_account, subordinates in master_data.items():
            for subordinate in subordinates:
                # Check if the subordinate account exists in the subordinate_data map
                if subordinate in subordinate_data:
                    subordinate_pages = subordinate_data[subordinate]
                    print(f"Processing {subordinate} with {len(subordinate_pages)} page(s).")

                    # Add the pages of the subordinate account
                    for page_num in subordinate_pages:
                        writer.add_page(reader.pages[page_num - 1])  # page_num is 1-indexed

                    # Check if the number of pages for this subordinate account is odd
                    if len(subordinate_pages) % 2 != 0:
                        print(f"Adding a blank page for {subordinate} (odd number of pages).")
                        
                        # Create and add a blank page
                        blank_page = create_blank_page()
                        blank_reader = PdfReader(blank_page)
                        writer.add_page(blank_reader.pages[0])

                    # Mark the subordinate account as processed
                    processed_subordinates.add(subordinate)
                else:
                    print(f"Warning: Subordinate account {subordinate} not found in subordinate data.")

        # Find remaining subordinate accounts
        remaining_subordinates = set(subordinate_data.keys()) - processed_subordinates
        print(f"Appending remaining subordinate accounts: {remaining_subordinates}")

        # Append the remaining subordinate accounts to the output PDF
        for subordinate in remaining_subordinates:
            subordinate_pages = subordinate_data[subordinate]
            print(f"Processing remaining subordinate {subordinate} with {len(subordinate_pages)} page(s).")

            # Add the pages of the subordinate account
            for page_num in subordinate_pages:
                writer.add_page(reader.pages[page_num - 1])  # page_num is 1-indexed

            # Check if the number of pages for this subordinate account is odd
            if len(subordinate_pages) % 2 != 0:
                print(f"Adding a blank page for {subordinate} (odd number of pages).")
                
                # Create and add a blank page
                blank_page = create_blank_page()
                blank_reader = PdfReader(blank_page)
                writer.add_page(blank_reader.pages[0])

        # Save the merged output
        with open(output_pdf_path, 'wb') as output:
            writer.write(output)

        print(f"PDF successfully created: {output_pdf_path}")




