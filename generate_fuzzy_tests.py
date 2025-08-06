import json
from openai import OpenAI
import argparse
from joblib import Parallel, delayed

def generate_fuzzy_tests(client,examples):

    example_strings = []
    for src,fuzzy_src,fuzzy_tgt,_ in examples:
      example_string = """Main sentence: {src}
      Fuzzy Match: {fuzzy_src}
      Translation: {fuzzy_tgt}
      """.format(src=src,fuzzy_src=fuzzy_src,fuzzy_tgt=fuzzy_tgt)

      example_strings.append(example_string)

    prompt = """Given a main source sentence in English, a fuzzy match of that source sentence, and a Finnish translation of that fuzzy match, produce three lists of tokens:
    
    1. tokens of the Finnish translation that semantically correspond to English tokens occurring in the main source and the fuzzy source
    2. tokens of the Finnish translation that semantically correspond to English tokens occurring only in the fuzzy match source.
    
    If a token corresponds only partially with the main sentence's English tokens, do not include it in the first list. The tokens should be in the lists in the same order as in the translation.

    Output the lists in the following JSON format: {{"positive_tokens": LIST1, "negative_tokens": LIST2}}

    Process the following example according to the above instructions:

    {examples}
    """.format(examples="\n".join(example_strings))

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
    parser.add_argument('--test_suite_path', type=str,
                        help='Test suite file containing the fuzzies for which to generate tests.')

    # Parse the arguments
    args = parser.parse_args()

    # Access the arguments
    api_key = args.api_key
    test_suite_path = args.test_suite_path
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/beta")

    with open(test_suite_path, 'r',encoding="utf8") as f:
        data = json.load(f)

    count = 0
    examples = []
    
    for example in data.get("examples", []):
        src = example.get("main_sentence")
        for fuzzy in example.get("fuzzy_matches", []):
            fuzzy_src = fuzzy.get("sentence")
            
            for translation in fuzzy.get("translations", []):
                if translation.get("validated"):
                    fuzzy_tgt = translation.get("target")
                    examples.append((src,fuzzy_src,fuzzy_tgt,translation))
                    count += 1
                    if len(examples) == 20:
                        results = Parallel(n_jobs=20, prefer="threads")(delayed(generate_fuzzy_tests)(client,[ex]) for ex in examples)
                        
                        for (_,_,_,translation_anchor),token_lists in zip(examples,results):
                            translation_anchor["tests"] = token_lists
                        print(f"processed {count} examples")
                        examples = []
                    

    with open(f'with_tests_{test_suite_path}', 'w') as term_json_file:
        json.dump(data, term_json_file, indent=4)

if __name__ == "__main__":
    main()