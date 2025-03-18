import csv
import openai 
from openai import OpenAI
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get OpenAI API key from environment variable
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

if not OPENAI_API_KEY:
    raise ValueError("OpenAI API key not found. Please set it in the .env file.")

# Set OpenAI API key
openai.api_key = OPENAI_API_KEY

# Define the evaluation prompt template for ChatCompletion
evaluation_prompt_template = """
You are an automated evaluator responsible for assessing chatbot responses based on **temporal accuracy** and **content relevance**. Below are the details for your evaluation:

**Question:**
{question}

**Chatbot Response:**
{response}

**Citation Dates Provided (from CSV):**
{dates}

**Important Instructions:**
1. **Temporal Accuracy:**
   - **Evaluate temporal accuracy solely based on the provided citation dates. Do not infer or assume dates from the response text itself.**
   - If the provided citation dates include sources from **2024** (High Weight), classify the response as **ACCEPTABLE** for temporal accuracy.
   - If the provided citation dates only include sources from **2023** (Medium Weight), classify the response as **ACCEPTABLE** if it supplements but does not replace 2024 sources.
   - If the response relies on older dates (2022 and earlier) or lacks citation dates entirely, classify it as **UNACCEPTABLE**.

2. **Content Relevance:**
   - Ensure that the response directly and comprehensively addresses the **Question**.
   - The content should be **clear**, **coherent**, and **focused** without introducing unrelated information.

3. **Graceful Failure:**
   - If the response indicates a lack of up-to-date information and suggests checking reliable sources, classify it as **ACCEPTABLE** for temporal accuracy and content relevance.
   - For example, responses like the following should be classified as **ACCEPTABLE**:
     - "I don't have enough information to provide a complete answer regarding [specific topic]. Please check [reliable sources] for the most accurate and up-to-date information."
     - "I'm not sure of the current status. Please consult recent updates from official sources."
   - However, responses that simply state, "I don't know," without suggesting next steps or reliable sources should be classified as **UNACCEPTABLE.**

**Evaluation Criteria:**
1. Classify the response as **ACCEPTABLE** or **UNACCEPTABLE** based on the provided citation dates and content relevance.
2. Provide a brief explanation for your classification.

**Classification:**
"""


def grade_response(question, response, dates):
    # Prepare the messages for ChatCompletion
    messages = [
        {"role": "system", "content": evaluation_prompt_template.format(
            question=question,
            response=response,
            dates=", ".join(dates) if dates else "None"
        )}
    ]

    print (dates)
    
    try:
        # Make API call to GPT-4 using the ChatCompletion endpoint
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",  # Use a compatible chat model
            messages=messages,
            max_tokens=200,
            temperature=0,  # Lower temperature for deterministic responses
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        classification = completion.choices[0].message.content.strip()
        return classification
    except Exception as e:
        print(f"Error grading response: {e}")
        return "ERROR"

def main():
    input_csv = 'evaluation_questions_with_responses.csv'        # Input CSV file
    output_csv = 'graded_evaluation_results.csv'                 # Output CSV file

    # Read the input CSV
    with open(input_csv, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)

    # Process each row
    for index, row in enumerate(rows, start=1):
        question = row['Question']
        podbot_response = row['PodBot Response']
        podbot_dates = [date.strip() for date in row['Podbot Citation Dates'].split(',')] if row['Podbot Citation Dates'] else []
        wikichat_response = row['WikiChat Response']
        wikichat_dates = [date.strip() for date in row['Wikichat Citation Dates'].split(',')] if row['Wikichat Citation Dates'] else []

        print(wikichat_dates)

        print(f"Processing Row {index}: '{question}'")

        # Grade PodBot response
        if podbot_response:
            podbot_classification = grade_response(question, podbot_response, podbot_dates)
        else:
            podbot_classification = "UNACCEPTABLE"  # No response provided
        row['PodBot Classification'] = podbot_classification

        # Grade WikiChat response
        if wikichat_response:
            wikichat_classification = grade_response(question, wikichat_response, wikichat_dates)
        else:
            wikichat_classification = "UNACCEPTABLE"  # No response provided
        row['WikiChat Classification'] = wikichat_classification

        # To comply with rate limits
        time.sleep(1)  # Adjust sleep time based on your API rate limits

    # Write the graded results to the output CSV
    with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
        # Define fieldnames (existing + new)
        fieldnames = reader.fieldnames + ['PodBot Classification', 'WikiChat Classification']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Grading completed. Results saved to '{output_csv}'.")

if __name__ == "__main__":
    main()


