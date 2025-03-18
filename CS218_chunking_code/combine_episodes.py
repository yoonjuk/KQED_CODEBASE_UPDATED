import os
import json
import argparse
from collections import defaultdict

def combine_jsonl_per_podcast(input_dir, output_dir):
    """
    Combines multiple JSONL files into a single JSONL file per podcast based on 'podcast_id'.
    
    Args:
        input_dir (str): Path to the directory containing JSONL files.
        output_dir (str): Path to the directory where combined JSONL files will be saved.
    """
    
    # Dictionary to hold podcast_id as key and list of JSON objects as value
    podcasts = defaultdict(list)
    
    # Traverse the input directory
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith('.jsonl'):
                file_path = os.path.join(root, file)
                print(f"Processing file: {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        for line_number, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue  # Skip empty lines
                            try:
                                json_obj = json.loads(line)
                                # Extract podcast_id from block_metadata
                                podcast_id = json_obj.get('block_metadata', {}).get('podcast_id', 'UNKNOWN_PODCAST')
                                # Optional: Extract document_title for naming
                                document_title = json_obj.get('document_title', 'Unknown_Podcast')
                                # Sanitize document_title to create a safe filename
                                sanitized_title = sanitize_filename(document_title)
                                # Store the JSON object
                                podcasts[podcast_id].append(json_obj)
                            except json.JSONDecodeError as e:
                                print(f"  [Error] JSON decoding failed in file {file_path} at line {line_number}: {e}")
                except Exception as e:
                    print(f"  [Error] Failed to read file {file_path}: {e}")
    
    # Ensure the output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Write combined JSONL files per podcast
    for podcast_id, json_objects in podcasts.items():
        # Use the first document_title as the podcast title
        first_obj = json_objects[0]
        document_title = first_obj.get('document_title', 'Unknown_Podcast')
        sanitized_title = sanitize_filename(document_title)
        
        # Define the output file path
        output_file = os.path.join(output_dir, f"{sanitized_title}_{podcast_id}.jsonl")
        
        print(f"Writing combined JSONL for Podcast ID {podcast_id} to {output_file}")
        
        try:
            with open(output_file, 'w', encoding='utf-8') as out_f:
                for obj in json_objects:
                    json_line = json.dumps(obj, ensure_ascii=False)
                    out_f.write(json_line + '\n')
        except Exception as e:
            print(f"  [Error] Failed to write to file {output_file}: {e}")

def sanitize_filename(name):
    """
    Sanitizes a string to be safe for use as a filename.
    
    Args:
        name (str): The original string.
    
    Returns:
        str: The sanitized string.
    """
    import re
    # Replace spaces and special characters with underscores
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    return sanitized

def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Combine multiple JSONL files into a single JSONL file per podcast.")
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='Path to the input directory containing JSONL files.'
    )
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='Path to the output directory where combined JSONL files will be saved.'
    )
    
    args = parser.parse_args()
    
    combine_jsonl_per_podcast(args.input_dir, args.output_dir)

if __name__ == "__main__":
    main()
