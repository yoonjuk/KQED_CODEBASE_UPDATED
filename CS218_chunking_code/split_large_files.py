import os

def split_jsonl(input_file, output_dir, lines_per_file=5000):
    """
    Splits a large JSONL file into smaller files.

    :param input_file: Path to the input JSONL file.
    :param output_dir: Directory where split files will be saved.
    :param lines_per_file: Number of lines per split file.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    file_count = 1
    current_line = 0
    output_file = os.path.join(output_dir, f"forum_split_{file_count}.jsonl")
    outfile = open(output_file, 'w', encoding='utf-8')

    with open(input_file, 'r', encoding='utf-8') as infile:
        for line in infile:
            outfile.write(line)
            current_line += 1
            if current_line >= lines_per_file:
                outfile.close()
                print(f"Created: {output_file} with {current_line} lines.")
                file_count += 1
                output_file = os.path.join(output_dir, f"forum_split_{file_count}.jsonl")
                outfile = open(output_file, 'w', encoding='utf-8')
                current_line = 0

    outfile.close()
    print(f"Created: {output_file} with {current_line} lines.")
    print("Splitting complete.")

if __name__ == "__main__":
    # Set the path to your input file
    INPUT_FILE = 'combined_jsonl_files_forum/Forum_from_KQED_f29d748b-939f-4fb6-b0fb-43e3e111b937.jsonl'

    # Set the output directory (you can name it as you prefer)
    OUTPUT_DIR = 'split_output'

    # Set the number of lines per split file (adjust as needed)
    LINES_PER_FILE = 5000

    split_jsonl(INPUT_FILE, OUTPUT_DIR, LINES_PER_FILE)


