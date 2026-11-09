# SourceDesk

Private on-device workbench for the Lenovo AI PC Hackathon, Problem C. Answers are quotes from the local files. A stitched sentence that adds a number, a name, or a date is dropped.

The round-1 write-up is `report/ShreedharGupta_IITK_ProblemC.docx`.

## What runs here

Indexing, separate word and 5-gram BM25 indexes, a 256-dimensional hashed mean pool, extractive quotes, a five-line summary, a draft that cannot add a figure, a version compare, a per-file refresh, a tier probe, and one CUDA forward pass on the laptop GPU. `train_later.py` prints the LoRA recipe from CS781 Module 4.1 and exits. It does not train.

## Smoke test

From this folder, with the packages in `requirements.txt` already installed:

```
python samples/make_samples.py
python tests/test_smoke.py
```

The fictional set is four office files and one low-confidence scan. Nothing in it is a real person.

Ask one question:

```
set PYTHONPATH=src
python -m sourcedesk samples "What is Rahul Verma's bonus?"
```
