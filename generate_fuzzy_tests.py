import json
from openai import OpenAI
import argparse

def generate_terms_and_tests(client,example,num_terms=5):

    input_format = """
{
      "fuzzy_matches": [
        {
          "type": "deletion",
          "similarity_estimate": 0.6065573770491803,
          "sentence": "Software update fixes a bug.",
          "validated": true,
          "translations": [
            {
              "target": "Ohjelmistopäivitys korjaa ohjelmistovirheen.",
            }
          ]
        }
      ],
      "main_sentence": "The software update will fix the security vulnerabilities.",
      "terms": {
        "software": [
          {
            "target": "ohjelmisto",
            "tests": [
              {
                "type": "term_present",
                "condition": "\\b[Oo]hjelmisto(.*)?\\b"
              }
            ],
            "selected": true
          },
          {
            "target": "tietokoneohjelma",
            "tests": [
              {
                "type": "term_present",
                "condition": "\\b[Tt]ietokoneohjelm(.*)?\\b"
              }
            ],
            "selected": true
          },
        ],
        "update": [
            {
                "target": "p\u00e4ivitys",
                "tests": [
                    {
                        "type": "term_present",
                        "condition": "\\b[Pp]\u00e4ivity(.*)?\\b"
                    }
                ]
            },
            {
                "target": "ohjelmistop\u00e4ivitys",
                "tests": [
                    {
                        "type": "term_present",
                        "condition": "\\b[Oo]hjelmistop\u00e4ivity(.*)?\\b"
                    }
                ]
            }
        ]
      }
    }
"""

    template = """
            {
          "type": "deletion",
          "similarity_estimate": 0.6065573770491803,
          "sentence": "Software update fixes a bug.",
          "validated": true,
          "translations": [
            {
              "target": "Ohjelmistopäivitys korjaa ohjelmistovirheen.",
              "tests": [
                    {
                        "type": "surface_form_present",
                        "condition": "\\b[Oo]hjelmistopäivity(.*)?\\b",
                        "term_conflict": "update"
                    },
                    {
                        "type": "surface_form_present",
                        "condition": "\\bkorjaa\\b"
                    },
                    {
                        "type": "construction_present",
                        "condition": "korjaa haavoittuvuudet"
                    },
                    {
                        "type": "surface_form_present",
                        "condition": "\\bohjelmistovirheen\\b",
                        "negative": "true"
                    }
                    ]
                }
              ]
              }"""

    prompt = """You are provided a JSON file of the following format:

    {input_format}

    Add tests to fuzzy matches. The purpose of these tests is to check if the fuzzy match has been properly utilized in a translation. They are similar to the term tests, but there are more types of fuzzy match tests. Here is an example of a fuzzy match with tests:

    {template}
    
    Tests of type surface_form_present are meant to check for parts of the fuzzy that should be present in the translation of the main sentence when utilizing the fuzzy. Tests of type construction_present are meant to check for linguistic constructions that should be present in the translation when utilizing the fuzzy. For instance, in the example fuzzy match above, the construction used in the fuzzy match is "SUBJECT korjaa OBJECT", so we use the test "korjaa haavoittuvuudet" to check that the translation uses the same construction.

    A special case are surface_form_present tests where the surface form corresponds to some term translation for the main sentence. In those cases, the test should have the "term_conflict": "true" property.

    }""".format(input_format=input_format,template=template)

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