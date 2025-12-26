"""
Convert UniProt IDs from Excel file to Entrez IDs and run herb prediction pipeline.

This script:
1. Reads UniProt IDs from an Excel file
2. Converts them to Entrez Gene IDs using UniProt REST API
3. Runs the main.py pipeline to train model and predict herbs
"""

import pandas as pd
import subprocess
import sys
import logging
from pathlib import Path
from uniprot_entrzid import map_uniprot_to_entrez

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('conversion.log', mode='w', encoding='utf-8')
    ]
)

def main():
    """Main function to orchestrate the conversion and prediction pipeline."""
    
    # Step 1: Read Excel file
    excel_file = Path("input_proteins.xlsx")
    
    if not excel_file.exists():
        logging.error(f"Excel file not found: {excel_file}")
        sys.exit(1)
    
    logging.info(f"Reading Excel file: {excel_file}")
    df = pd.read_excel(excel_file)
    
    if 'Entry' not in df.columns:
        logging.error("Column 'Entry' not found in Excel file!")
        logging.error(f"Available columns: {list(df.columns)}")
        sys.exit(1)
    
    uniprot_ids = df['Entry'].dropna().unique().tolist()
    logging.info(f"Found {len(uniprot_ids)} unique UniProt IDs")
    logging.info(f"UniProt IDs: {uniprot_ids}")
    
    # Step 2: Convert UniProt IDs to Entrez IDs
    logging.info("Converting UniProt IDs to Entrez Gene IDs...")
    mapping = map_uniprot_to_entrez(uniprot_ids)
    
    # Save mapping to CSV
    mapping_df = pd.DataFrame([
        {'UniProt_ID': uid, 'Entrez_ID': gid}
        for uid, gid in mapping.items()
    ])
    mapping_file = Path("uniprot_to_entrez_mapping.csv")
    mapping_df.to_csv(mapping_file, index=False)
    logging.info(f"Mapping saved to: {mapping_file}")
    
    # Display mapping results
    logging.info("\nMapping Results:")
    logging.info("-" * 60)
    successful = 0
    failed = 0
    entrez_ids = []
    
    for uid, gid in mapping.items():
        if gid:
            logging.info(f"  {uid} -> {gid}")
            # Handle multiple GeneIDs (separated by semicolon)
            if ';' in gid:
                # Take the first one
                first_gid = gid.split(';')[0]
                entrez_ids.append(first_gid)
                logging.info(f"    Note: Multiple GeneIDs found, using first one: {first_gid}")
            else:
                entrez_ids.append(gid)
            successful += 1
        else:
            logging.warning(f"  {uid} -> NOT FOUND")
            failed += 1
    
    logging.info("-" * 60)
    logging.info(f"Successfully mapped: {successful}/{len(uniprot_ids)}")
    logging.info(f"Failed to map: {failed}/{len(uniprot_ids)}")
    
    if not entrez_ids:
        logging.error("No valid Entrez IDs found. Cannot proceed with prediction.")
        sys.exit(1)
    
    # Step 3: Run main.py with the Entrez IDs
    entrez_ids_str = ",".join(entrez_ids)
    logging.info(f"\nPreparing to run herb prediction with Entrez IDs: {entrez_ids_str}")
    logging.info("=" * 60)
    logging.info("Starting main.py pipeline...")
    logging.info("=" * 60)
    
    try:
        # Run main.py with the converted Entrez IDs
        cmd = [sys.executable, "main.py", "--entrez_ids", entrez_ids_str]
        logging.info(f"Command: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, check=True, capture_output=False, text=True)
        
        logging.info("=" * 60)
        logging.info("Pipeline completed successfully!")
        logging.info("=" * 60)
        logging.info("Check the outputs/ directory for results.")
        
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running main.py: {e}")
        logging.error("Check run.log in the outputs directory for details.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()


