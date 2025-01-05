from utils import extract_master_data, extract_subordinate_data, reorder_and_merge

def main():
    # File paths
    master_pdf = "data/Master.pdf"
    subordinate_pdf = "data/Subordinate.pdf"
    output_pdf = "data/Output.pdf"
    
    # Extract data
    #print("Extracting data from Master PDF...")
    master_data = extract_master_data(master_pdf)
    
    #print("Extracting data from Subordinate PDF...")
    subordinate_data = extract_subordinate_data(subordinate_pdf)
    
    # Reorder and merge
    #print("Reordering and merging PDFs...")
    reorder_and_merge(master_data, subordinate_data, subordinate_pdf, output_pdf)
    
    print(f"PDF successfully created: {output_pdf}")

if __name__ == "__main__":
    main()
