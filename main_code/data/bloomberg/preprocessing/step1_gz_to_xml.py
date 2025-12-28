# This code takes the raw zipped xml files and extracts them to xml files

import os
import gzip
import shutil
from concurrent.futures import ThreadPoolExecutor

# Define source and destination directories
source_dir = "H:/data_common_master/Bloomberg_News/raw/"
destination_dir = "H:/data_common_master/Bloomberg_News/xml/"

# Ensure the destination directory exists
os.makedirs(destination_dir, exist_ok=True)

def extract_file(file_path):
    """Extract a single .gz file to the destination directory."""
    try:
        # Get the base filename without .gz
        base_name = os.path.basename(file_path)
        output_file = os.path.join(destination_dir, base_name[:-3])  # Remove .gz
        
        # Decompress the file
        with gzip.open(file_path, 'rb') as gz_file:
            with open(output_file, 'wb') as xml_file:
                shutil.copyfileobj(gz_file, xml_file)
        
        print(f"Extracted: {file_path} -> {output_file}")
    except Exception as e:
        print(f"Failed to extract {file_path}: {e}")

def main():
    # Get all .gz files in the source directory
    gz_files = [os.path.join(source_dir, f) for f in os.listdir(source_dir) if f.endswith('.gz')]


    # Parallelize the extraction process
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(extract_file, gz_files)

if __name__ == "__main__":
    main()
