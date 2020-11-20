from __future__ import unicode_literals
from __future__ import print_function
import re
import plac
import random
from pathlib import Path
import spacy
import json
import logging

LABEL = "COL_NAME"

def trim_entity_spans(data: list) -> list:
  """Removes leading and trailing white spaces from entity spans.

  Args:
    data (list): The data to be cleaned in spaCy JSON format.

  Returns:
    list: The cleaned data.
  """
  invalid_span_tokens = re.compile(r'\s')

  cleaned_data = []
  for text, annotations in data:
    entities = annotations['entities']
    valid_entities = []
    for start, end, label in entities:
      valid_start = start
      valid_end = end
      while valid_start < len(text) and invalid_span_tokens.match(text[valid_start]):
        valid_start += 1
      while valid_end > 1 and invalid_span_tokens.match(text[valid_end - 1]):
        valid_end -= 1
      valid_entities.append([valid_start, valid_end, label])
    cleaned_data.append([text, {'entities': valid_entities}])

  return cleaned_data


def convert_dataturks_to_spacy(dataturks_JSON_FilePath):
  try:
    training_data = []
    lines = []
    with open(dataturks_JSON_FilePath, 'r', encoding="utf8") as f:
      lines = f.readlines()

    for line in lines:
      data = json.loads(line)
      text = data['content']
      entities = []
      if data['annotation'] is not None:
        for annotation in data['annotation']:
          # only a single point in text annotation.
          point = annotation['points'][0]
          labels = annotation['label']
          # handle both list of labels or a single label.
          if not isinstance(labels, list):
            labels = [labels]

          for label in labels:
            # dataturks indices are both inclusive [start, end]
            # but spacy is not [start, end)
            entities.append((point['start'], point['end'] + 1, label))

      training_data.append((text, {"entities": entities}))
    return training_data
  except Exception:
    logging.exception("Unable to process " + dataturks_JSON_FilePath)
    return None


TRAIN_DATA = trim_entity_spans(convert_dataturks_to_spacy("./training/data/traindata.json"))

@plac.annotations(
  model=("Model name. Defaults to blank 'en' model.", "option", "m", str),
  new_model_name=("New model name for model meta.", "option", "nm", str),
  output_dir=("Optional output directory", "option", "o", Path),
  n_iter=("Number of training iterations", "option", "n", int),
)

def main(
  model=None,
  new_model_name="resume_parser_model",
  output_dir='./models/resume_entity_parser',
  n_iter=5
):
  """Set up the pipeline and entity recognizer, and train the new entity."""
  random.seed(0)
  if model is not None:
    nlp = spacy.load(model)  # load existing spaCy model
    print("Loaded model '%s'" % model)
  else:
    nlp = spacy.blank("en")  # create blank Language class
    print("Created blank 'en' model")
  # Add entity recognizer to model if it's not in the pipeline
  # nlp.create_pipe works for built-ins that are registered with spaCy

  if "ner" not in nlp.pipe_names:
    print("Creating new pipe")
    ner = nlp.create_pipe("ner")
    nlp.add_pipe(ner, last=True)

  # otherwise, get it, so we can add labels to it
  else:
    ner = nlp.get_pipe("ner")

  # add labels
  for _, annotations in TRAIN_DATA:
    for ent in annotations.get('entities'):
      ner.add_label(ent[2])

  # if model is None or reset_weights:
  #     optimizer = nlp.begin_training()
  # else:
  #     optimizer = nlp.resume_training()
  # move_names = list(ner.move_names)
  # get names of other pipes to disable them during training
  other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]
  with nlp.disable_pipes(*other_pipes):  # only train NER
    optimizer = nlp.begin_training()
    # batch up the examples using spaCy's minibatch
    for itn in range(n_iter):
      print("Starting iteration " + str(itn))
      random.shuffle(TRAIN_DATA)
      losses = {}
      for text, annotations in TRAIN_DATA:
        try:
          nlp.update(
            [text],  # batch of texts
            [annotations],  # batch of annotations
            drop=0.2,  # dropout - make it harder to memorise data
            sgd=optimizer,  # callable to update weights
            losses=losses
          )
        except Exception:
          pass
      print("Losses", losses)

  # save model to output directory
  if output_dir is not None:
    output_dir = Path(output_dir)
    if not output_dir.exists():
      output_dir.mkdir()
    nlp.meta["name"] = new_model_name  # rename model
    nlp.to_disk(output_dir)
    print("Saved model to", output_dir)

if __name__ == "__main__":
  plac.call(main)
