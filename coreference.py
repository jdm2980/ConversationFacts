#import en_coref_md
import spacy
from nltk import CFG, ChartParser
import parse
from parse import Entry

nlp = spacy.load('en') # requires you to run 'python -m spacy download en'
#nlp2 = en_coref_md.load()
data = parse.parse()

# THIS SECTION IS USING NEURALCOREF WHICH WILL PROBABLY NOT BE USED
# pip install cython
# pip install https://github.com/huggingface/neuralcoref-models/releases/download/en_coref_md-3.0.0/en_coref_md-3.0.0.tar.gz
# install NeuralCoref from https://github.com/huggingface/neuralcoref
# changed to spacy 2.0.13
#for entry in data[:5]:
#    for summary in entry.summaries_sentences[0]:
#        print(summary)
#        doc = nlp2(summary)
#        if doc._.has_coref:
#            print(doc._.coref_clusters)
#        print()

# This is for dialogues
#line = 0
#for entry in data[:10]:
#    for dialogue in entry.dialog:
#        print(dialogue)
#        doc = nlp(dialogue)
#        sentence = next(doc.sents)
#        for word in sentence:
#            if word.text == 'I' or word.text == 'i':
#                if line % 2 == 0:
#                    print(word.text + ':S1')
#                else:
#                    print(word.text + ':S2')
#            if word.text == 'You' or word.text == 'you':
#                if line % 2 == 0:
#                    print(word.text + ':S2')
#                else:
#                    print(word.text + ':S1')
#        line += 1
#        print()

# This is for summaries
stored = ''
for entry in data[1:2]:
    for summaries in entry.summaries_sentences:
        for summary in summaries:
            print(summary)
            doc = nlp(summary)
            sentence = next(doc.sents)
            for word in sentence:
                print(word.dep_, end=" ")
            print()
            for idx, word in enumerate(sentence):
                if word.dep_ == 'compound':
                    stored = word.text
                    break
                elif word.text == "This":
                    if sentence[idx + 1].text == 'person':
                        print(word.text + ' ' + sentence[idx + 1].text + ':' + stored)
                        break
                elif word.dep_ == 'nsubj':
                    if word.text == 'They' or word.text == 'He' or word.text == 'She':
                        if sentence[idx + 1].text == 'or' and sentence[idx + 2].dep_ is 'conj':
                            print(word.text + ' ' + sentence[idx + 1].text + ' ' + sentence[idx + 2].text, end="")
                            print(":" + stored)
                            break
                        print(word.text, end="")
                        print(":" + stored)
                        break
                    else:
                        stored = word.text
                        if sentence[idx + 1].text == 'and' and sentence[idx + 2].dep_ is 'conj':
                            stored += ' ' + sentence[idx + 1].text + ' ' + sentence[idx + 2].text
                        break
            print(stored)
            print()