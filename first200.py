import PyPDF2

# Open the original PDF
with open('data/Subordinate.pdf', 'rb') as infile:
    reader = PyPDF2.PdfReader(infile)
    writer = PyPDF2.PdfWriter()

    # Extract the first 200 pages
    for page_num in range(200):
        writer.add_page(reader.pages[page_num])

    # Save the new PDF with only the first 200 pages
    with open('data/Subordinate-20Pages.pdf', 'wb') as outfile:
        writer.write(outfile)

print("New PDF with the first 20 pages has been created.")
