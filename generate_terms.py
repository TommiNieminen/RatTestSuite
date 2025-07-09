import json
from openai import OpenAI
import argparse

def generate_terms_and_tests(client,example,num_terms=5):

    template = """
{
    "terms": {
        "security": [
        {
            "target": "suojaus",
            "tests": [
                {
                    "type": "term_present",
                    "condition": "\\b[Ss]uojau[ks](.*)?\\b"
                }
            ]
        },
        {
            "target": "turvallisuus",
            "tests": [
                {
                    "type": "term_present",
                    "condition": "\\b[Tt]urvallisuu(.*)?\\b"
                }
            ]
        },
        ],
        "software": [
        {
            "target": "tietokoneohjelma",
            "tests": [
                {
                    "type": "term_present",
                    "condition": "\\b[Tt]ietokoneohjelm(.*)?\\b"
                }
            ]
        },
        {
            "target": "ohjelmisto",
            "tests": [
                {
                    "type": "term_present",
                    "condition": "\\b[Oo]hjelmisto(.*)?\\b"
                }
            ]
        },
        {
            "target": "ohjelmistotuote",
            "tests": [
                {
                    "type": "term_present",
                    "condition": "\\b[Oo]hjelmistotuot(.*)?\\b"
                }
            ]
        }
        ]
    }
}
    """

    prompt = """Generate terms and their Finnish translations from a main sentence. The terms should be phrases for which there are multiple possible translations into Finnish (for instance the word "security" would have the two possible translations "suojaus" and "turvallisuus"). Output 5 alternative translations as possible for each term. The terms should be phrases specific to a certain domain that are actually used, and they should be either noun or verb phrases. Different target variants should be linguistically similar, i.e. all verbs or all nouns, not a mix of verbs and nouns. The terms should be formal, do not use informal language in them. The terms should in the lemma form, i.e. not inflected and always in the singular. Prefer short single word terms.

    In addition to the target sides of term, provide for each target side a regular expression that can be used to check that the target side is present in a Finnish translation of the sentence. The tests should take into account the possible inflection of the target terms, as well as recognizing both capitalized and non-capitalized forms.

    Output the terms as JSON, using the following format (where the sentence is "The software update will fix the security vulnerabilities."):
        
    {template}

    Generate a maximum of {num_terms} terms. The sentence to generate terms from is {sentence}""".format(num_terms=num_terms,sentence=example["main_sentence"],template=template)

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
                        help='Test suite file containing the sentences for which to generate terms.')
    parser.add_argument('--num_terms', type=int, default=5,
                        help='Max number of terms to generate per source sentence (default: 5)')

    # Parse the arguments
    args = parser.parse_args()

    # Access the arguments
    api_key = args.api_key
    test_suite_path = args.test_suite_path
    num_terms = args.num_terms
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/beta")

    with open(test_suite_path, 'r') as f:
        data = json.load(f)

    for example in data["examples"]:
        terms = generate_terms_and_tests(client,example,num_terms)
        example["terms"] = terms["terms"]

    with open(f'with_terms_{test_suite_path}', 'w') as term_json_file:
        json.dump(data, term_json_file, indent=4)

if __name__ == "__main__":
    main()