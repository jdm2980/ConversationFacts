""" Parses the nldslab json into a custom formatted object """

import collections
import json
import os
import pickle
import re
import sys

import spacy
from nltk.tokenize import sent_tokenize, word_tokenize

JSON_FILE_PATH = 'data.json'

REPLACE_DICT = {
    "don't": "do not",
    "it's": "it is",
    "doesn't": "does not",
    "It's": "It is",
    "I'm": "I am",
    "that's": "that is",
    "isn't": "is not",
    "can't": "can not",
    "didn't": "did not",
    "you're": "you are",
    "You're": "You are",
    "shouldn't": "should not",
    "That's": "That is",
    "aren't": "are not",
    "they're": "they are",
    "I'd": "I would",
    "I've": "I have",
    "I'll": "I will",
    "wasn't": "was not",
    "couldn't": "could not",
    "there's": "there is",
    "Speaker one": "S1",
    "Speaker two": "S2",
    "speaker one": "S1",
    "speaker two": "S2",
    "you'd": "you would",
    "You'd": "you would",

    "he/she": "they",
    "his/her": "their",
    "He/she": "they",
    "him/her": "them",
    "and/or": "either or both"
}


class Entry:
    def __init__(self, key, dialog, summary, summary_to_dialog):
        self.key = key
        self.dialog = dialog
        self.summaries = summary
        self.dialog_raw = dialog

        self.summary_to_dialog = [dict(), dict(), dict(), dict(), dict()]
        for i, summary in enumerate(summary_to_dialog):
            for value in summary:
                sen, dialog = value.split(',')
                if (sen not in self.summary_to_dialog[i]):
                    self.summary_to_dialog[i][sen] = set()
                self.summary_to_dialog[i][sen].add(dialog)


def parse(refresh=False):
    """ Return Entry object list with preprocessed text """

    if (not refresh):
        if (os.path.isfile('./parse.p')):
            print('Reading data from saved object file "parse.p" pass boolean to force refresh')
            return pickle.load(open('./parse.p', 'rb'))
        else:
            print('Saved data obj "parse.p" does not exist, refreshing')
            return parse(True)
    else:
        with open(JSON_FILE_PATH) as file:
            data = json.load(file)
            entries = []
            for entry in data:
                entries.append(
                    Entry(entry['key'], entry['Dialog'], entry['Summary'], entry['Summary_to_dialog']))

    entries = replace_bad_words(entries)
    # count_bad_words(entries)

    entries = clean_dialog(entries)
    entries = clean_summaries(entries)

    # comment this out to run coreference.py
    entries = coreference(entries)

    if (refresh):
        print('Saving data object to "parse.p"')
        pickle.dump(entries, open('./parse.p', 'wb'))

    return entries


def count_bad_words(data):
    """ Counts number of words contaning ' and / which are split by SpaCy """

    counter = collections.Counter()

    for entry in data:
        token_dialog = word_tokenize(entry.dialog)
        for i, token in enumerate(token_dialog):
            if "'" in token:
                counter[token_dialog[i-1] + token] += 1
            if "/" in token:
                counter[token] += 1

        token_summary = word_tokenize(entry.summaries)
        for i, token in enumerate(token_summary):
            if "'" in token:
                counter[token_summary[i-1] + token] += 1
            if "/" in token:
                counter[token] += 1
    print(counter.most_common())


def replace_bad_words(data):
    """ Replace words in text based on REPLACE_DICT """

    # http://code.activestate.com/recipes/81330-single-pass-multiple-replace/
    regex = re.compile("(%s)" % "|".join(map(re.escape, REPLACE_DICT.keys())))

    for entry in data:
        entry.dialog = regex.sub(
            lambda rbw: REPLACE_DICT[rbw.string[rbw.start():rbw.end()]], entry.dialog)
        entry.summaries = regex.sub(
            lambda rbw: REPLACE_DICT[rbw.string[rbw.start():rbw.end()]], entry.summaries)

    return data


def coreference(data):
    """ Removes ambiguous pronouns from data """

    nlp = spacy.load('en')
    stored = ''
    for entry in data:
        for line, dialog in enumerate(entry.dialog):
            if line % 2 == 0:
                entry.dialog[line] = entry.dialog[line].replace('You ', 'S2 ')
                entry.dialog[line] = entry.dialog[line].replace('you ', 'S2 ')
                entry.dialog[line] = entry.dialog[line].replace('I ', 'S1 ')
                entry.dialog[line] = entry.dialog[line].replace(' Me ', ' S1 ')
                entry.dialog[line] = entry.dialog[line].replace(' me ', ' S1 ')
            else:
                entry.dialog[line] = entry.dialog[line].replace('You ', 'S1 ')
                entry.dialog[line] = entry.dialog[line].replace('you ', 'S1 ')
                entry.dialog[line] = entry.dialog[line].replace('I ', 'S2 ')
                entry.dialog[line] = entry.dialog[line].replace(' Me ', ' S2 ')
                entry.dialog[line] = entry.dialog[line].replace(' me ', ' S2 ')
        for count, summaries in enumerate(entry.summaries_sentences):
            summaries = list(entry.summaries_sentences[count])
            for num, doc in enumerate(summaries):
                sentence = nlp(doc)
                for idx, word in enumerate(sentence):
                    if word.dep_ == 'compound':
                        stored = word.text
                        break
                    elif word.text == "This":
                        if sentence[idx + 1].text == 'person':
                            summaries[num] = summaries[num].replace(
                                word.text + ' ' + sentence[idx + 1].text, stored, 1)
                            break
                    elif word.dep_ == 'nsubj':
                        if word.text == 'They' or word.text == 'He' or word.text == 'She':
                            if sentence[idx + 1].text == 'or' and sentence[idx + 2].dep_ is 'conj':
                                summaries[num] = summaries[num].replace(
                                    word.text + ' ' + sentence[idx + 1].text + ' ' + sentence[idx + 2].text, stored, 1)
                                break
                            summaries[num] = summaries[num].replace(word.text, stored, 1)
                            break
                        else:
                            stored = word.text
                            if sentence[idx + 1].text == 'and' and sentence[idx + 2].dep_ is 'conj':
                                stored += ' ' + sentence[idx + 1].text + \
                                    ' ' + sentence[idx + 2].text
                            break
            entry.summaries_sentences[count] = summaries
    return data


def clean_summaries(data):
    """ Split summary value into individual summaries and individual sentences """

    for entry in data:
        # split summary list
        entry.summaries = [re.sub('-*\n', '', str_).strip()
                           for str_ in re.split('D[0-9"()]', entry.summaries)[1:]]
        # create list of sentences from summaries
        entry.summaries_sentences = [sent_tokenize(summary) for summary in entry.summaries]
        # remove unnecessary punctuation
        entry.summaries_sentences = [(re.sub('[/\\-.,"()]', '', sentence).strip()
                                      for sentence in summary) for summary in entry.summaries_sentences]
    return data


def clean_dialog(data):
    """ Split dialog by speaker and remove exteraneous tokens"""

    for entry in data:
        # split dialog by speaker and remove special characters
        entry.dialog = re.sub(r'\([^)]*\)', '', entry.dialog)  # remove everything between ()'s
        entry.dialog = re.sub('[?!]', '.', entry.dialog)  # change all punction to periods
        entry.dialog = re.sub('\.+', '.', entry.dialog)  # change '..' or longer
        entry.dialog = [re.sub('[/\\-"()]', '',  str_).strip()
                        for str_ in re.split('S[0-9]:[0-9]+-', entry.dialog)[1:]]

        # remove sentences shorter than 6 words
        for i, dialog in enumerate(entry.dialog):
            new_dialog = ''
            for sentence in dialog.split('.'):
                if len(sentence.split(' ')) >= 6:
                    new_dialog += sentence + '.'
            entry.dialog[i] = new_dialog

        entry.dialog_raw = [re.sub('\s+', ' ', str_).strip()
                            for str_ in re.split('S[0-9]:[0-9]+-', entry.dialog_raw)[1:]]

    return data


if (__name__ == '__main__'):
    if (len(sys.argv) != 2):
        print("Please run command with desired conversation/summary ID, EX: 'py parse.py 0'")
    elif (int(sys.argv[1]) < 0 or int(sys.argv[1]) > 44):
        print("Argument out of range (0,44)")
    else:
        data = parse(False)
        current = data[int(sys.argv[1])]

        print(current.key)
        for i, dialog in enumerate(current.dialog):
            print(str(i) + ' : ' + dialog)

        print('...')
        for i, summary in enumerate(current.summaries):
            print(str(i) + ' : ' + summary)
