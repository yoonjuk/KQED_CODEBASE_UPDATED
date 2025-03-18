import json
import uuid
from datetime import datetime, timezone
import nltk
from nltk.tokenize import sent_tokenize
import firebase_admin
from firebase_admin import credentials, storage, firestore
import re
import sys
import os
import logging
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Set to WARNING to reduce output; adjust as needed
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("peepee2.log")  # Optional: logs to a file
    ]
)

# Initialize NLTK's punkt tokenizer
nltk.download('punkt')

# Initialize Firebase Admin SDK
SERVICE_ACCOUNT_PATH = 'podbot-f6540-firebase-adminsdk-ay94m-58455aa724.json'  # Replace with your service account path
BUCKET_NAME = 'podbot-f6540.appspot.com'  # Replace with your Firebase Storage bucket name

if not os.path.exists(SERVICE_ACCOUNT_PATH):
    logging.critical(f"Service account file not found at: {SERVICE_ACCOUNT_PATH}")
    sys.exit(1)

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_PATH)
    firebase_admin.initialize_app(cred, {
        'storageBucket': BUCKET_NAME
    })
    bucket = storage.bucket()
    logging.info("Firebase initialized successfully.")
except Exception as e:
    logging.critical(f"Failed to initialize Firebase app: {e}")
    sys.exit(1)

# Initialize Firestore
db = firestore.client()

# Define helper functions
def download_file_from_blob(bucket, blob_path):
    """
    Downloads a file from Firebase Storage using its blob path.
    """
    blob = bucket.blob(blob_path)
    if not blob.exists():
        logging.error(f"File not found at path: {blob_path}")
        raise Exception(f"File not found at path: {blob_path}")
    return blob.download_as_text()

def chunk_text(text, chunk_size=500):
    """
    Splits text into chunks of approximately chunk_size words without splitting sentences.
    """
    sentences = sent_tokenize(text)
    chunks = []
    current_chunk = ""
    current_word_count = 0

    for sentence in sentences:
        sentence_word_count = len(sentence.split())
        if current_word_count + sentence_word_count <= chunk_size:
            current_chunk += " " + sentence
            current_word_count += sentence_word_count
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence
            current_word_count = sentence_word_count

    # Add the last chunk
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def create_chunk_json(document_title, section_title, content, last_edit_date, url, timestamp_start, timestamp_end, block_metadata):
    """
    Creates a dictionary representing a single chunk in the desired JSON format.
    """
    chunk_json = {
        "document_title": document_title,
        "section_title": section_title,
        "content": content,
        "last_edit_date": last_edit_date,
        "url": url,
        "block_metadata": {
            **block_metadata,
            "timestamp_start": timestamp_start,
            "timestamp_end": timestamp_end
        }
    }

    return chunk_json

def sanitize_folder_name(name):
    """
    Sanitizes folder and file names by:
    - Replacing spaces and specified special characters with dashes.
    - Removing any remaining unwanted characters.
    - Converting to lowercase for consistency.
    """
    # Replace spaces with dashes
    name = re.sub(r'\s+', '-', name)

    # Replace special characters with dashes
    name = re.sub(r'[<>:"/\\|?*\'`]', '-', name)

    # Remove any characters that are not alphanumeric or dashes
    name = re.sub(r'[^a-zA-Z0-9\-]', '', name)

    # Replace multiple consecutive dashes with a single dash
    name = re.sub(r'-{2,}', '-', name)

    # Convert to lowercase
    name = name.lower()

    return name

def parse_json_transcription(transcription_json):
    """
    Parses the JSON transcription to extract word-level data.
    """
    try:
        words = transcription_json['results']['channels'][0]['alternatives'][0]['words']
        word_data = []
        for word_info in words:
            word = word_info.get('word', '')
            start = word_info.get('start', 0.0)  # in seconds
            end = word_info.get('end', 0.0)      # in seconds
            speaker_tag = word_info.get('speaker', 'UNKNOWN')
            word_data.append({
                'word': word,
                'start': start,
                'end': end,
                'speaker_tag': speaker_tag
            })
        return word_data
    except (KeyError, IndexError) as e:
        logging.error(f"Error parsing JSON transcription: {e}")
        return []

def align_chunks_with_timestamps(chunks, word_data):
    """
    Aligns text chunks with word-level timestamps to assign start and end times.
    """
    aligned_chunks = []
    current_word_index = 0
    total_words = len(word_data)

    for chunk in chunks:
        chunk_words = chunk.split()
        num_words = len(chunk_words)

        if current_word_index >= total_words:
            # No more words to assign
            chunk_start_time = 0
            chunk_end_time = 0
            logging.warning(f"No more words to assign for chunk: '{chunk[:30]}...'")
        else:
            # Assign start and end times based on word data
            chunk_start_time = word_data[current_word_index]['start']
            end_index = current_word_index + num_words - 1
            if end_index < total_words:
                chunk_end_time = word_data[end_index]['end']
            else:
                chunk_end_time = word_data[-1]['end']
            logging.debug(f"Chunk '{chunk[:30]}...' assigned start: {chunk_start_time}, end: {chunk_end_time}")

        aligned_chunks.append({
            'chunk_content': chunk,
            'timestamp_start': chunk_start_time,
            'timestamp_end': chunk_end_time
        })

        current_word_index += num_words

    return aligned_chunks

def assign_speakers_to_chunks(aligned_chunks, document_title, section_title, last_edit_date, block_metadata):
    """
    Assigns speakers to each chunk and prepares the final JSON structure.
    """
    structured_chunks = []

    # Sanitize folder names
    sanitized_document_title = sanitize_folder_name(document_title)
    sanitized_section_title = sanitize_folder_name(section_title)

    for chunk in aligned_chunks:
        # Generate a unique identifier for the chunk using timestamps
        # Format: chunk_{timestamp_start}_{timestamp_end}.json
        # To ensure filenames are filesystem-friendly, replace '.' with 'p'
        # Example: chunk_0p16_183p015.json
        ts_start = str(chunk['timestamp_start']).replace('.', 'p')
        ts_end = str(chunk['timestamp_end']).replace('.', 'p')
        chunk_filename = f"chunk_{ts_start}_{ts_end}.json"

        # Define the storage path for this chunk
        chunk_folder_path = f'224v/{sanitized_document_title}/{sanitized_section_title}'
        chunk_blob_path = f'{chunk_folder_path}/{chunk_filename}'

        # Construct the URL
        chunk_url = f'https://storage.googleapis.com/{BUCKET_NAME}/{chunk_blob_path}'

        # Update block_metadata with the URL if necessary
        updated_block_metadata = block_metadata.copy()
        # Add or modify fields in block_metadata here if needed

        # **Convert speakers list to a single string**
        if 'speakers' in updated_block_metadata and isinstance(updated_block_metadata['speakers'], list):
            updated_block_metadata['speakers'] = ", ".join(updated_block_metadata['speakers'])
        else:
            updated_block_metadata['speakers'] = "UNKNOWN"

        # Create the chunk JSON with timestamps inside block_metadata
        chunk_json = create_chunk_json(
            document_title=document_title,
            section_title=section_title,
            content=chunk['chunk_content'],
            last_edit_date=last_edit_date,
            url=chunk_url,
            timestamp_start=chunk['timestamp_start'],
            timestamp_end=chunk['timestamp_end'],
            block_metadata=updated_block_metadata
        )
        structured_chunks.append(chunk_json)

    return structured_chunks

def process_episode(episode, podcast_title, podcast_description, bucket, BUCKET_NAME):
    """
    Processes a single podcast episode: downloads transcriptions, chunks text, assigns speakers and timestamps, and uploads chunk JSONs.
    """
    try:
        # Extract episode details
        episode_id = episode['episode_id']
        section_title = episode['section_title']
        speakers = episode.get('speakers', [])
        last_edit_timestamp = episode.get('last_edit_date')
        txt_blob_path = episode['transcription_raw_text_path']
        json_blob_path = episode.get('raw_transcription_json_path') or episode.get('json_url')

        # Convert 'last_edit_date' from milliseconds to 'YYYY-MM-DD' format using timezone-aware datetime
        if last_edit_timestamp:
            try:
                last_edit_date = datetime.fromtimestamp(last_edit_timestamp / 1000, tz=timezone.utc).strftime('%Y-%m-%d')
            except Exception as e:
                last_edit_date = 'Invalid Timestamp'
                logging.error(f"Error converting timestamp for episode {episode_id}: {e}")
        else:
            last_edit_date = 'Unknown'

        logging.info(f"Processing Episode: {section_title}")

        # Download TXT transcription
        if txt_blob_path:
            txt_content = download_file_from_blob(bucket, txt_blob_path)
            logging.info(f"   * TXT transcription downloaded for Episode: {section_title}")
        else:
            logging.warning(f"   * No TXT transcription path for Episode: {section_title}")
            return

        # Download JSON transcription
        if json_blob_path:
            json_content = download_file_from_blob(bucket, json_blob_path)
            transcription_json = json.loads(json_content)
            logging.info(f"   * JSON transcription downloaded for Episode: {section_title}")
        else:
            transcription_json = {}
            logging.warning(f"   * No JSON transcription path for Episode: {section_title}")

        # Parse word-level data
        if transcription_json:
            word_data = parse_json_transcription(transcription_json)
            if not word_data:
                logging.warning(f"   * No word data extracted for Episode: {section_title}")
        else:
            word_data = []

        # Chunk the transcription
        chunks = chunk_text(txt_content, chunk_size=500)
        logging.info(f"   * Created {len(chunks)} chunks for Episode: {section_title}")

        # Prepare block_metadata
        block_metadata = {
            "block_type": "text",
            "language": "en",
            "podcast_id": episode['podcast_id'],
            "podcast_description": podcast_description,
            "speakers": speakers
        }

        # Align chunks with timestamps
        aligned_chunks = align_chunks_with_timestamps(chunks, word_data)

        # Assign speakers and prepare structured chunks without 'chunk #'
        structured_chunks = assign_speakers_to_chunks(
            aligned_chunks,
            document_title=podcast_title,
            section_title=section_title,
            last_edit_date=last_edit_date,
            block_metadata=block_metadata
        )
        logging.info(f"   * Structured chunks prepared for Episode: {section_title}")

        # Upload structured chunks
        for chunk_json in structured_chunks:
            chunk_folder_path = f'224v/{sanitize_folder_name(podcast_title)}/{sanitize_folder_name(section_title)}'
            # Extract timestamp_start and timestamp_end from block_metadata
            ts_start = str(chunk_json['block_metadata']['timestamp_start']).replace('.', 'p')
            ts_end = str(chunk_json['block_metadata']['timestamp_end']).replace('.', 'p')
            chunk_filename = f"chunk_{ts_start}_{ts_end}.json"
            chunk_blob_path = f'{chunk_folder_path}/{chunk_filename}'

            # Upload to Firebase Storage
            blob = bucket.blob(chunk_blob_path)
            blob.upload_from_string(json.dumps(chunk_json, indent=2), content_type='application/json')
            logging.info(f"   * Uploaded Chunk to: {chunk_blob_path}")

        # Save structured chunks locally (optional)
        local_filename = f"{episode_id}_chunks.jsonl"
        with open(local_filename, 'w', encoding='utf-8') as f:
            for chunk_json in structured_chunks:
                f.write(json.dumps(chunk_json) + '\n')
        logging.info(f"   * Structured chunks saved locally as '{local_filename}'.\n")

    except Exception as e:
        logging.error(f"   * Failed to process Episode {section_title}: {e}")

if __name__ == "__main__":
    # Define the podcast ID you want to process
    PODCAST_ID = 'f29d748b-939f-4fb6-b0fb-43e3e111b937'  # Replace with your desired podcast ID

    # Fetch podcast details from Firestore
    podcasts_ref = db.collection('podcasts')
    podcast_doc = podcasts_ref.document(PODCAST_ID).get()
    if podcast_doc.exists:
        podcast_data = podcast_doc.to_dict()
        podcast_title = podcast_data.get('name', 'Unknown Podcast')  # Correct field
        podcast_description = podcast_data.get('description', 'No Description')
    else:
        podcast_title = "Unknown Podcast"
        podcast_description = "No Description"
        logging.warning(f"Podcast with ID {PODCAST_ID} does not exist.")

    # Reference to the 'audios' collection
    audios_ref = db.collection('audios')

    # Query for episodes where 'podcastsId' matches the specified PODCAST_ID
    query = audios_ref.where('podcastsId', '==', PODCAST_ID)

    # Execute the query
    try:
        episodes = query.stream()
        logging.info(f"Fetching episodes for Podcast ID: {PODCAST_ID}\n")
    except Exception as e:
        logging.error(f"An error occurred while querying Firestore: {e}")
        sys.exit(1)

    # Initialize a list to hold episode data
    episode_data_list = []

    # Iterate through the fetched episodes
    for episode in episodes:
        data = episode.to_dict()

        # Extract required fields
        episode_info = {
            'episode_id': episode.id,
            'podcast_id': data.get('podcastId') or data.get('podcastsId'),
            'section_title': data.get('episode_title') or data.get('description', 'Untitled Section'),
            'speakers': list(data.get('speakers', {}).values()) if data.get('speakers') else [],
            'last_edit_date': data.get('episode_at'),
            'json_url': data.get('json_url', ''),
            'raw_transcription_json_path': data.get('rawTranscriptionJsonPath', ''),
            'transcription_raw_text_path': data.get('transcriptionRawTextPath') or data.get('text_url', '')
        }

        # Validate required fields (exclude 'speakers' as it's optional now)
        required_fields = ['section_title', 'last_edit_date', 'transcription_raw_text_path']
        missing_fields = [field for field in required_fields if not episode_info.get(field)]
        if missing_fields:
            logging.warning(f"Episode {episode.id} is missing fields: {missing_fields}. Skipping.")
            continue

        # Ensure 'speakers' is always a list
        episode_info['speakers'] = episode_info.get('speakers', [])

        episode_data_list.append(episode_info)

    # Check if any episodes were found
    if not episode_data_list:
        logging.warning(f'No valid episodes found for Podcast ID: {PODCAST_ID}')
        sys.exit(0)

    # Optional: Display the extracted episode data
    # (Consider removing or setting a higher logging level to reduce output)
    for idx, episode in enumerate(episode_data_list, start=1):
        logging.debug(f"Episode {idx}:")
        logging.debug(f"  Podcast ID       : {episode['podcast_id']}")
        logging.debug(f"  Episode ID       : {episode['episode_id']}")
        logging.debug(f"  Section Title    : {episode['section_title']}")
        logging.debug(f"  Speakers         : {episode['speakers']}")

        # Convert 'last_edit_date' from milliseconds to a readable date format
        # This step is now handled inside process_episode

    # ==============================
    # 6. Process Each Episode Concurrently
    # ==============================

    # Define the maximum number of threads
    MAX_THREADS = 10  # Adjust based on your system and Firebase's rate limits

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []
        for episode in episode_data_list:
            futures.append(executor.submit(
                process_episode,
                episode,
                podcast_title,
                podcast_description,
                bucket,
                BUCKET_NAME
            ))

        # Optionally, wait for all futures to complete
        concurrent.futures.wait(futures)

    logging.info("All episodes have been processed.")








