"""
Batch convert all JSON files in a folder to NWB format
"""
import os
import sys
import logging
from pathlib import Path

# Add the current directory to path to import TransferToNWB
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from TransferToNWB import bonsai_to_nwb

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def batch_convert_json_to_nwb(input_folder, output_folder=None):
    """
    Convert all JSON files in input_folder to NWB format
    
    Parameters
    ----------
    input_folder : str
        Path to folder containing JSON files
    output_folder : str, optional
        Path to save NWB files. If None, uses input_folder
    """
    input_folder = Path(input_folder)
    
    if not input_folder.exists():
        logger.error(f"Input folder does not exist: {input_folder}")
        return
    
    if output_folder is None:
        output_folder = input_folder
    else:
        output_folder = Path(output_folder)
        output_folder.mkdir(parents=True, exist_ok=True)
    
    # Find all JSON files
    json_files = list(input_folder.glob("*.json"))
    
    if not json_files:
        logger.warning(f"No JSON files found in {input_folder}")
        return
    
    logger.info(f"Found {len(json_files)} JSON files to convert")
    logger.info(f"Output folder: {output_folder}")
    
    results = []
    for json_file in json_files:
        logger.info(f"Processing: {json_file.name}")
        try:
            result = bonsai_to_nwb(str(json_file), str(output_folder))
            results.append((json_file.name, result))
            logger.info(f"  Result: {result}")
        except Exception as e:
            results.append((json_file.name, f"error: {str(e)}"))
            logger.error(f"  Error: {str(e)}")
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("CONVERSION SUMMARY")
    logger.info("="*60)
    
    success_count = sum(1 for _, r in results if r == "success")
    incomplete_count = sum(1 for _, r in results if r == "incomplete_json")
    empty_count = sum(1 for _, r in results if r == "empty_trials")
    error_count = sum(1 for _, r in results if "error" in r)
    
    logger.info(f"Total files processed: {len(results)}")
    logger.info(f"  Successful: {success_count}")
    logger.info(f"  Incomplete JSON: {incomplete_count}")
    logger.info(f"  Empty trials: {empty_count}")
    logger.info(f"  Errors: {error_count}")
    
    if error_count > 0:
        logger.info("\nFiles with errors:")
        for fname, result in results:
            if "error" in result:
                logger.info(f"  {fname}: {result}")


if __name__ == "__main__":
    # Default path
    default_input_folder = r"H:\Anna_optical_tagging_json"
    
    if len(sys.argv) < 2:
        input_folder = default_input_folder
        output_folder = None
        logger.info(f"Using default input folder: {input_folder}")
    else:
        input_folder = sys.argv[1]
        output_folder = sys.argv[2] if len(sys.argv) > 2 else None
    
    batch_convert_json_to_nwb(input_folder, output_folder)
