# Chunking Script

This folder contains scripts to process podcast transcripts into metadata-rich chunks and combine them into single JSONL files per podcast for upload to WikiChat.

---

## How to Use

### Step 1: Retrieve Podcast ID

1. Go to Firebase and locate the Podcast ID for the series you want to process.
2. Open `final_chunk_one.py` and replace this line:
   ```python
   PODCAST_ID = 'f29d748b-939f-4fb6-b0fb-43e3e111b937'
   with the desired Podcast ID.
   ```

### Step 2: Run the Chunking Script

1. Run final_chunk_one.py to process the transcripts into 500-word chunks:
   python3 final_chunk_one.py
2. This will generate individual JSONL files containing chunks for each episode of the podcast.

### Step 3: Combine JSONL Files

1. Run combine_episode.py to merge the JSONL files for all episodes of a podcast into a single JSONL file:
   ython3 combine_episode.py --input_dir path/to/chunked_files --output_dir path/to/combined_files
2. The combined JSONL file will include all the episode chunks in one file, formatted for WikiChat upload.

### Step 4(optional): Split JSONL File

1. If Wikichat is having trouble with big file upload, you can use split_large_files.py to split your JSONL file into multiple ones
