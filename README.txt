These scripts and programs are for constructing a test suite for retrieval-augmented machine translation (MT) evaluation.

The test suite consists of test cases, which in turn consist of source sentences and units of retrieved information (matches) that may be provided to the MT system during translation. Currently two types of information are included: terms and fuzzy matches. Both terms and fuzzy may have multiple translations, and each of the translations is paired with regular expression tests which check if the match is correctly utilized in the translation. Evaluation is done by having a translation system supporting retrieval augmentation translate the source sentences with the matches, and then running the tests on the produced translations.

# Building the test suite

The test suite is built semiautomatically using an LLM (currently with DeepSeek, although modifying for other LLMs should be simple). As LLMs tend to fail when producing a large amount of data with complex instructions, the task is split into multiple steps, and manual validation steps are performed inbetween the automatic steps. Here are the steps for creating a test suite of about 100 test cases:

1. Generate a set of source sentences, which should have around 150 sentences to allow for rejections (automatic)
2. Generate a set of fuzzy source language sentences for the sentences created in step 1 (automatic)
3. Exclude problematic source sentences and fuzzies (manual, validate_fuzzies.py)
4. Generate translations for each fuzzy (automatic)
5. Generate max 5 terms per source sentence and term tests for each term (automatic)
6. Select usable terms, discarding sentences for which no usable terms are available (manual, validate_terms.py)
7. Generate fuzzy tests (automatic)
8. Go through the produced test suite file fixing tests (manual)
