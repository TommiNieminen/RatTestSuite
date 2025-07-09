import json
from openai import OpenAI
import Levenshtein
import copy
import argparse

def update_similarity_estimates(main_sentence, unfiltered_data, removal_threshold):
    """
    Reads a JSON string, computes normalized Levenshtein distance for fuzzy matches,
    updates similarity_estimate, removes matches below threshold, and returns the modified JSON.
    
    Args:
        json_string (str): JSON string containing the data to process.
        removal_threshold (float): Threshold below which fuzzy matches will be removed (0.0-1.0).
    
    Returns:
        dict: Updated JSON data with recalculated similarity_estimates and filtered matches.
    """

    data = copy.deepcopy(unfiltered_data)

    filtered_matches = []
    
    for fuzzy_match in data['fuzzy_matches']:
        fuzzy_sentence = fuzzy_match['sentence']
        
        # Compute normalized Levenshtein distance (0-1, where 1 is identical)
        distance = Levenshtein.distance(main_sentence, fuzzy_sentence)
        max_len = max(len(main_sentence), len(fuzzy_sentence))
        normalized_similarity = 1 - (distance / max_len) if max_len > 0 else 1.0
        
        # Update the similarity_estimate
        fuzzy_match['similarity_estimate'] = normalized_similarity
        
        # Keep only matches above the threshold
        if normalized_similarity >= removal_threshold:
            filtered_matches.append(fuzzy_match)
    
    # Replace the fuzzy_matches with the filtered list
    data['fuzzy_matches'] = filtered_matches

    return data



def generate_main_sentences(client, example_count):
    prompt = f"""Generate  {example_count} English sentences from the IT, electronics, medical and legal domains. The sentences should come from three length categories, short (10-15 words), medium (16-25 words), and long (25-40 words). Only output the sentences with no explanation. Use the following format: INDEX_NUMBER ||| LENGTH CATEGORY ||| DOMAIN  ||| SENTENCE""".format(example_count=example_count)

    prefix = "1 ||| short ||| electronics ||| Remember to turn off the machine before cleaning it."

    response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                #{"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": prefix,"prefix": True}
            ],
            temperature=0,max_tokens=8000,
            stream=False
        )
        
    answer = response.choices[0].message.content
    return answer

def generate_fuzzies(client,sentence, example_count=20):

    template = """
        {
            "fuzzy_matches": 
            [
                {
                    "type": "deletion",
                    "similarity_estimate": 0.7,
                    "sentence": "Update to the latest version."
                },
                {
                    "type": "addition",
                    "similarity_estimate": 0.7,
                    "sentence": "Please update the software to the latest version immediately."
                },
                {
                    "type": "replacement",
                    "similarity_estimate": 0.9,
                    "sentence": "Upgrade the software to the newest version."
                    
                }
            ]
        }"""

    prompt = """Generate fuzzy matches for the following main sentence: {sentence}

    A fuzzy match is sentence whose lexical similarity with the main sentence exceeds a certain threshold. The lexical similarity is calculated as a normalized edit distance, and it can be a value between 0 to 1. The threshold that we use for a fuzzy match 0.7. The generated fuzzy matches should be grammatically correct and semantically different from the main sentence.

    Output the fuzzy matches as json, using the following template:
    
    {template}

    There are three fuzzy types (mark the category in the file for each fuzzy):
    1. Deletion fuzzies: Fuzzy is shorter than the main sentence, and the fuzzy is mostly identical with a part of the main sentence. Example: a deletion fuzzy for the source sentence "Turn off the device before leaving" could be "Turn off the device".
    2.  Addition fuzzies: Fuzzy is longer than the main sentence, and a part of the fuzzy is mostly identical with the main sentence. Example: an addition fuzzy for the source sentence "Turn off the device before leaving" could be "Remember to turn off the device before leaving".
    3. Replacement fuzzies: Fuzzy is mostly the same length as the main sentence, but part or parts of the fuzzy differ from the main sentence. Example: a replacement fuzzy for the source sentence "Turn off the device before leaving" could be "Turn off the machine before leaving" or "Deactivate the device before leaving". 

    The fuzzy matches should be as varied as possible. For instance, the fuzzies should not all start with the same phrase. Fuzzy matches must be complete and believable sentences. Fuzzies must be semantically different from the main sentence, i.e. not just paraphrases, but they must still retain lexical similarity of at least 70 percent. For instance, if there is a number in the main sentence, use a different number in the fuzzy, and if there is technical term in the main sentence, use a different technical term. 

    Generate {example_count} fuzzies.""".format(example_count=example_count,sentence=sentence,template=template)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            #{"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],    
        response_format={
            'type': 'json_object'
        },
        temperature=0,max_tokens=8000,
        stream=False
    )
        
    answer = response.choices[0].message.content
    data = json.loads(answer)
    return data

def main():
    # Initialize the argument parser
    parser = argparse.ArgumentParser(description="Process some parameters for an API.")

    # Add arguments
    parser.add_argument('--api-key', type=str, required=True,
                        help='API key for authentication')
    parser.add_argument('--sentences', type=int, default=5,
                        help='Number of sentences to generate (default: 5)')
    parser.add_argument('--fuzzies', type=int, default=3,
                        help='Number of fuzzy matches to return (default: 3)')
    parser.add_argument('--threshold', type=float, default=0.7,
                        help='Fuzzy matching threshold (default: 0.7)')

    # Parse the arguments
    args = parser.parse_args()

    # Access the arguments
    api_key = args.api_key
    num_sentences = args.sentences
    num_fuzzies = args.fuzzies
    fuzzy_threshold = args.threshold
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/beta")

    main_sentences = generate_main_sentences(client, num_sentences)

    data = {"examples": []}
    for sentence_row in main_sentences.split("\n"):
        # skip first empty row
        if "|||" not in sentence_row:
            continue
        index,length,domain,sentence = sentence_row.split("|||")
        sentence_fuzzies = generate_fuzzies(client, sentence, num_fuzzies)
        filtered_sentence_fuzzies = update_similarity_estimates(sentence,sentence_fuzzies,fuzzy_threshold)
        filtered_sentence_fuzzies["main_sentence"] = sentence
        data["examples"].append(filtered_sentence_fuzzies)

    with open('fuzzies.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

if __name__ == "__main__":
    main()