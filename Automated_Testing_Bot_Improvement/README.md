# Automated Testing Script

This folder contains scripts to evaluate the performance of Podbot and WikiChat by grading responses to curated queries using GPT-4O.

## Overview

The script allows you to input a CSV file containing test queries and chatbot responses, and outputs a CSV file with evaluation results. It evaluates the accuracy of Podbot and WikiChat's responses based on predefined criteria using GPT-4O.

## Input Format

Prepare a CSV file with the following column headers:

- **ID**: Unique identifier for each query.
- **Question**: The test query to be evaluated.
- **PodBot Response**: The response provided by Podbot.
- **PodBot Citation Dates**: Any citation or publication dates included in Podbot's response.
- **WikiChat Response**: The response provided by WikiChat.
- **WikiChat Citation Dates**: Any citation or publication dates included in WikiChat's response.
- **PodBot Classification**: Leave this blank for the script to populate the evaluation result.
- **WikiChat Classification**: Leave this blank for the script to populate the evaluation result.

### Example Input (`queries.csv`)

| ID  | Question                         | PodBot Response                 | PodBot Citation Dates | WikiChat Response  | WikiChat Citation Dates | PodBot Classification | WikiChat Classification |
| --- | -------------------------------- | ------------------------------- | --------------------- | ------------------ | ----------------------- | --------------------- | ----------------------- |
| 1   | What should I know about Prop 6? | Prop 6 is about...              | 2018                  | Prop 6 aims to...  | 2024                    |                       |                         |
| 2   | Are we at risk of wildfires?     | Yes, wildfires are a concern... | 2017                  | Yes, as of 2024... | 2024                    |                       |                         |

## Output Format

The script generates a new CSV file with the classification results appended for both Podbot and WikiChat.

### Example Output

| ID  | Question                         | PodBot Response                 | PodBot Citation Dates | WikiChat Response  | WikiChat Citation Dates | PodBot Classification   | WikiChat Classification |
| --- | -------------------------------- | ------------------------------- | --------------------- | ------------------ | ----------------------- | ----------------------- | ----------------------- |
| 1   | What should I know about Prop 6? | Prop 6 is about...              | 2018                  | Prop 6 aims to...  | 2024                    | UNACCEPTABLE because... | ACCEPTABLE because...   |
| 2   | Are we at risk of wildfires?     | Yes, wildfires are a concern... | 2017                  | Yes, as of 2024... | 2024                    | UNACCEPTABLE because... | ACCEPTABLE because...   |

## How to Run

1. **Install OpenAI**:  
   Before running the script, install the `openai` library:
   ```bash
   pip install openai
   ```
