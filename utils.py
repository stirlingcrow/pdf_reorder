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
    
    print(f"-------Staring Master Account PDF Analysis---------")
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
    Returns a dictionary where the key is the subordinate account number,
    and the value contains associated pages and the bunchcode.
    Blank pages are included in the tracked pages for each account.
    """
    subordinate_data = {}  # Dictionary to store subordinate account information
    current_account_number = None  # Current subordinate account being processed
    current_pages = []  # Pages associated with the current account
    current_bunchcode = None  # Bunchcode for the current account

    print("------- Starting Subordinate Page Analysis -------")
    
    with pdfplumber.open(subordinate_pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            lines = text.splitlines() if text else []  # Split text into lines or set to an empty list if no text

            # Detect the start of a new account when "Page 1 of" is present
            if len(lines) > 2 and "Page 1 of" in lines[2]:
                # Extract the account number from the 6th line (if present)
                if len(lines) > 5:
                    account_line = lines[5]
                    account_match = re.search(r'(\d{9}) - (\d{7})', account_line)
                    if account_match:
                        new_account_number = f"{account_match.group(1)} - {account_match.group(2)}"

                        # Extract the bunchcode (always the last line on page 1)
                        new_bunchcode = lines[-1].strip() if lines else ""

                        # If processing a new account, save the current account's data
                        if current_account_number:
                            subordinate_data[current_account_number] = {
                                'pages': current_pages,
                                'bunchcode': current_bunchcode
                            }

                        # Start tracking the new account
                        current_account_number = new_account_number
                        current_bunchcode = new_bunchcode
                        current_pages = [page_num]  # Start fresh with the new account's first page

                        print(f"Detected New Account: {current_account_number} (Bunchcode: {current_bunchcode})")
                        continue
            
            # Continue adding pages to the current account, even if blank
            if current_account_number:
                current_pages.append(page_num)

        # Save the last account's data after the loop
        if current_account_number:
            subordinate_data[current_account_number] = {
                'pages': current_pages,
                'bunchcode': current_bunchcode
            }

    # Print extracted subordinate data for review
    print("------- Extracted Subordinate Data -------")
    for account_number, data in subordinate_data.items():
        print(f"Account: {account_number}")
        print(f"  Bunchcode: {data['bunchcode']}")
        print(f"  Total Pages: {len(data['pages'])}")
        print(f"  Pages: {[f'Page {page}' for page in data['pages']]}")

    return subordinate_data



def extract_subordinate_data_old(subordinate_pdf_path):
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
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            lines = text.splitlines()  # Split the page text into lines
            
            if len(lines) > 2 and "Page 1 of" in lines[2]:
                # Extract the account number from the 6th line (e.g., "26-DEC-2024 022222800 - 2200002 - 7 RIO RANCHO, NM")
                if len(lines) > 5:  
                    account_line = lines[5]  
                    match = re.search(r'(\d{9}) - (\d{7})', account_line)  
                    if match:
                        account_number = f"{match.group(1)} - {match.group(2)}"
                        
                        # Extract BUNCHCODE from the last line of page 1 for each account
                        last_line = lines[-1]  # Get the last line of the page
                        bunchcode = last_line.strip()  # Strip any whitespace and assign to bunchcode
                        if not bunchcode:
                            print(f"No BUNCHCODE found for account {account_number} - defaulting to blank")
                            bunchcode = ''
                        
                        # If we've encountered a new account and it's not the first page, store the previous account's data
                        if current_account_number and current_pages:
                            subordinate_data[current_account_number] = {'pages': current_pages, 'bunchcode': bunchcode}
                        
                        # Start tracking the new account and its pages
                        current_account_number = account_number
                        print(f"Working On Account: {current_account_number}")
                        current_pages = [page_num]
                    else:
                        continue
            else:
                if current_account_number:
                    current_pages.append(page_num)
                    
        # After the loop, store the last account's data if it exists
        if current_account_number and current_pages:
            subordinate_data[current_account_number] = {'pages': current_pages, 'bunchcode': bunchcode}
    

    # Print extracted subordinate data for review
    print("Extracted Subordinate Data:")
    for account_number, data in subordinate_data.items():
        print(f"Account: {account_number}")
        print(f"  Bunchcode: {data['bunchcode']}")
        print(f"  Total Pages: {len(data['pages'])}")  # Print the total number of pages for the account
        print(f"  Pages: {[f'Page {page}' for page in data['pages']]}")  
        
    return subordinate_data


def reorder_and_merge(master_data, subordinate_data, subordinate_pdf_path, output_pdf_path):
    """
    Reorders and merges Subordinate PDF pages based on Master PDF structure.
    Adds a blank page if a subordinate account has an odd number of pages.
    Appends unprocessed subordinate accounts grouped by bunchcode and sorted alphanumerically.
    """
    writer = PdfWriter()
    processed_subordinates = set()  # To track processed subordinate accounts
    total_pages_processed = 0  # To track the total pages processed

    print(f"-------Starting PDF Creation and Reorder---------")
    
    # Open the Subordinate PDF
    with open(subordinate_pdf_path, 'rb') as f:
        reader = PdfReader(f)

        print(f"--Working Through Accounts In Master File--")
        # Process subordinate accounts based on the Master Account structure
        for master_account, subordinates in master_data.items():
            for subordinate in subordinates:
                if subordinate in subordinate_data:
                    subordinate_pages = subordinate_data[subordinate]['pages']
                    print(f"Processing {subordinate} with {len(subordinate_pages)} page(s).")

                    # Add the pages of the subordinate account
                    for page_num in subordinate_pages:
                        writer.add_page(reader.pages[page_num - 1])  # page_num is 1-indexed
                        total_pages_processed += 1

                    # Add a blank page if odd number of pages
                    if len(subordinate_pages) % 2 != 0:
                        print(f"Adding a blank page for {subordinate} (odd number of pages).")
                        blank_page = create_blank_page()
                        blank_reader = PdfReader(blank_page)
                        writer.add_page(blank_reader.pages[0])
                        total_pages_processed += 1

                    # Mark the subordinate account as processed
                    processed_subordinates.add(subordinate)
                else:
                    print(f"Warning: Subordinate account {subordinate} not found in subordinate data.")

        # Find remaining subordinate accounts
        remaining_subordinates = set(subordinate_data.keys()) - processed_subordinates

        # Group remaining accounts by bunchcode
        grouped_by_bunchcode = {}
        for subordinate in remaining_subordinates:
            bunchcode = subordinate_data[subordinate]['bunchcode']
            if bunchcode not in grouped_by_bunchcode:
                grouped_by_bunchcode[bunchcode] = []
            grouped_by_bunchcode[bunchcode].append(subordinate)

        # Sort accounts within each bunchcode group
        for bunchcode in grouped_by_bunchcode:
            grouped_by_bunchcode[bunchcode].sort()

        print(f"--Working Through Accounts NOT In Master File, Grouped By Bunchcode--")
        # Append the remaining accounts in grouped and sorted order
        for bunchcode, accounts in sorted(grouped_by_bunchcode.items()):
            print(f"Processing bunchcode {bunchcode} with {len(accounts)} account(s).")
            for subordinate in accounts:
                subordinate_pages = subordinate_data[subordinate]['pages']
                print(f"  Processing subordinate {subordinate} with {len(subordinate_pages)} page(s).")

                # Add the pages of the subordinate account
                for page_num in subordinate_pages:
                    writer.add_page(reader.pages[page_num - 1])  # page_num is 1-indexed
                    total_pages_processed += 1

                # Add a blank page if odd number of pages
                if len(subordinate_pages) % 2 != 0:
                    print(f"Adding a blank page for {subordinate} (odd number of pages).")
                    blank_page = create_blank_page()
                    blank_reader = PdfReader(blank_page)
                    writer.add_page(blank_reader.pages[0])
                    total_pages_processed += 1

        # Save the merged output
        with open(output_pdf_path, 'wb') as output:
            writer.write(output)

        # Verify that all pages are accounted for
        total_original_pages = len(reader.pages)
        print(f"Total pages in original Subordinate PDF: {total_original_pages}")
        print(f"Total pages processed into new PDF: {total_pages_processed}")

        if total_original_pages == total_pages_processed:
            print("Success: All pages from the original PDF were processed.")
        else:
            print("Warning: Some pages may be missing in the output PDF.")


def reorder_and_merge_old(master_data, subordinate_data, subordinate_pdf_path, output_pdf_path):
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
        
        
        
def see_data(pdf_path):
    """
    Extracts data from the Master PDF, including the order of Subordinate Accounts.
    """
    master_data = {}
    
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text()
            # Implement pattern matching to extract Master and Subordinate Accounts
            # For now, we'll just log the text (modify as needed)
            #print(f"Page {page_num}: {text[:400]}...") # Preview first 100 characters
            print(f"Page {page_num}: {text}")  # Show entire page text
            print("--------------------------")

    # Example: Storing dummy data for testing
    master_data[page_num] = text # Store the full text or parsed results

    # Print the final master_data for debugging
    print("Data Extracted:")
    
    for key, value in master_data.items():
        print(f"Page {key}: {value[:200]}...") # Print a preview of each page's data

    return master_data



