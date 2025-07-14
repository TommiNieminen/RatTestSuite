import json
from openai import OpenAI
import Levenshtein
import copy
import argparse
from joblib import Parallel, delayed
import multiprocessing
import itertools

def check_for_main_sentence_similarity(main_sentence, generated_so_far, threshold=0.8):
    # Compute normalized Levenshtein distance (0-1, where 1 is identical)
    for existing_main_sentence in generated_so_far:
        distance = Levenshtein.distance(main_sentence.split(), existing_main_sentence.split())
        max_len = max(len(main_sentence.split()), len(existing_main_sentence.split()))
        normalized_similarity = 1 - (distance / max_len) if max_len > 0 else 1.0
        if normalized_similarity > threshold:
            return existing_main_sentence
    return None

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
        fuzzy_sentence_split = fuzzy_match['sentence'].split()
        main_sentence_split = main_sentence.split()
        # Compute normalized Levenshtein distance (0-1, where 1 is identical)
        distance = Levenshtein.distance(main_sentence_split, fuzzy_sentence_split)
        max_len = max(len(main_sentence_split), len(fuzzy_sentence_split))
        normalized_similarity = 1 - (distance / max_len) if max_len > 0 else 1.0
        
        # Update the similarity_estimate
        fuzzy_match['similarity_estimate'] = normalized_similarity
        
        # Keep only matches above the threshold
        if normalized_similarity >= removal_threshold:
            filtered_matches.append(fuzzy_match)
    
    # Replace the fuzzy_matches with the filtered list
    data['fuzzy_matches'] = filtered_matches

    return data

def generate_main_sentences_for_domain_and_length(client,example_count,domain,length_range):
    template = '{"index": INDEX, "terms": [TERMS GO HERE], "sentence": "SENTENCE GOES HERE"}'

    prompt = """Generate {example_count} English sentences from the {domain} domain. The sentences should have {length_range} words.

    The sentences should contain at least two terms which be translated in different ways into Finnish. The sentences should be structurally varied, and consist mostly of instructions and descriptions. Do not use semicolons in the sentences.

    Output the sentences as a json file with the main element 'sentences', and each sentence with the following template {template}. Make sure there are exactly {example_count} sentences. Do not stop generation until the index number is {example_count}. The terms should not be marked up in the sentence, only in the 'terms' field.""".format(example_count=example_count,template=template,domain=domain,length_range=length_range)

    response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                #{"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
                #{"role": "assistant", "content": prefix,"prefix": True}
            ],   
            response_format={
                'type': 'json_object'
            },
            temperature=0.1,max_tokens=8000, # Some variation is desired
            stream=False
        )
        
    answer = response.choices[0].message.content
    json_answer = json.loads(answer)
    for sentence in json_answer["sentences"]:
        sentence["domain"] = domain
    return json_answer

def generate_main_sentences(client, example_count):

    # TODO: When generating a lot of sentences, the style of the sentences becomes uniform. Generate the
    # domain sentences separately to reduce this effect.

    domains = ["medical","pharmaceutical","public administration","EU texts","IT administration","IT customer support", "electronics","legal"]

    length_ranges = ["10-20","20-30","30-40"]

    dom_len_combinations = list(itertools.product(domains,length_ranges))

    results = Parallel(n_jobs=8, prefer="threads")(delayed(generate_main_sentences_for_domain_and_length)(client,example_count,domain,length_range) for (domain,length_range) in dom_len_combinations)

    sentences = []
    generated_so_far = []
    for result in results:
        # Remove sentences that are too similar to each other
        for test_case in list(result["sentences"]):
            main_sentence = test_case["sentence"]
            similar_existing_sentence = check_for_main_sentence_similarity(main_sentence, generated_so_far)
            if similar_existing_sentence:
                # Remove the test case for too mucn similarity
                result["sentences"] = [x for x in result["sentences"] if x["sentence"] != main_sentence]
                print(f"Too similar to existing: {main_sentence}.\nExisting: {similar_existing_sentence}")
            else:
                generated_so_far.append(main_sentence)
        sentences = sentences + result['sentences']
         
    return sentences

def generate_deletion_fuzzies(client,sentence,num_fuzzies=5):
    template = json.dumps({"type": "deletion","sentence": "Update to the latest version."})
    prompt = f"Remove a semantically significant part from the following sentence while making sure the sentence remains grammatical and meaningful: {sentence}. Output {num_fuzzies} that differ from each other as much as possible. Output the sentences as JSON with the root node fuzzy_matches using the following template for each sentence: {template}"

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
    return json.loads(answer)

def generate_addition_fuzzies(client,sentence,num_fuzzies=5):
    template = json.dumps({"type": "addition","sentence": "Update to the latest version."})
    prompt = f"Add a semantically significant part (maximum length 10 percent of the sentence length) to the following sentence while making sure the sentence remains grammatical and meaningful: {sentence}. The addition should be continuous. Output {num_fuzzies} variants that differ from each other as much as possible. Output the sentences as JSON with the root node fuzzy_matches using the following template for each sentence: {template}"

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
    return json.loads(answer)

def generate_replacement_fuzzies(client,sentence,num_fuzzies=5):
    template = json.dumps({"type": "replacement","sentence": "Update to the latest version."})
    prompt = f"Substitute a part (maximum length 10 percent of the sentence length) of the following sentence with a semantically different part while making sure the sentence remains grammatical and meaningful: {sentence}. The substitution should be continuous. Output {num_fuzzies} variants that differ from each other as much as possible. Output only the sentences without indexes. Output the sentences as JSON with the root node fuzzy_matches using the following template for each sentence: {template}"

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
    return json.loads(answer)

def create_and_filter_fuzzies(client,sentence_json,num_fuzzies, fuzzy_threshold):
    domain = sentence_json["domain"]
    sentence = sentence_json["sentence"]

    del_fuzzies = generate_deletion_fuzzies(client,sentence,num_fuzzies)
    add_fuzzies = generate_addition_fuzzies(client,sentence,num_fuzzies)
    repl_fuzzies = generate_replacement_fuzzies(client,sentence,num_fuzzies)

    all_fuzzies = {"fuzzy_matches": del_fuzzies["fuzzy_matches"] + repl_fuzzies["fuzzy_matches"] + add_fuzzies["fuzzy_matches"]}

    filtered_sentence_fuzzies = update_similarity_estimates(sentence,all_fuzzies,fuzzy_threshold)
    filtered_sentence_fuzzies["main_sentence"] = sentence
    filtered_sentence_fuzzies["domain"] = domain

    return filtered_sentence_fuzzies

"""def create_and_filter_fuzzies(client, sentence_row, num_fuzzies, fuzzy_threshold):
    index,length,domain,sentence = sentence_row.split("|||")
    sentence_fuzzies = generate_fuzzies(client, sentence, num_fuzzies)
    filtered_sentence_fuzzies = update_similarity_estimates(sentence,sentence_fuzzies,fuzzy_threshold)
    filtered_sentence_fuzzies["main_sentence"] = sentence
    return filtered_sentence_fuzzies"""

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

    data = {}
    
    results = Parallel(n_jobs=8, prefer="threads")(delayed(create_and_filter_fuzzies)(client,sentence_row,num_fuzzies,fuzzy_threshold) for sentence_row in main_sentences)
    data["examples"] = results

    with open(f'phase1_and_2_{num_sentences}.json', 'w') as json_file:
        json.dump(data, json_file, indent=4)

if __name__ == "__main__":
    main()