import sys
from collections import Counter

import gensim
import nltk
import spacy
from gensim import models, similarities, summarization, utils
from nltk import word_tokenize

import generatekgs
import parse
from parse import Entry

nlp = spacy.load('en')
print('Spacy loaded')


def calc_rarewords(data, N=3):
    """ Returns tokens that appear less or equal to N times"""

    # build global conversation token list
    tokens = []
    for entry in data:
        for dialog in entry.dialog:
            tokens += word_tokenize(dialog.lower())

    rarewords = set([tup[0] for tup in Counter(tokens).most_common() if tup[1] <= N])

    return rarewords


def evaluate(data, rarewords, start, stop):
    """ Calculates effectiveness of model using tfidf, rarewords, and S# labeling """

    total_evaluated, total_correct, random_correct = 0, 0.0, 0.0

    for i, entry in enumerate(data[start:stop]):
        generatekgs.generate_kgs(i)  # make sure graph files are for correct conversation

        # build local conversation dict
        texts = []
        for dialog in entry.dialog:
            texts.append(list(word_tokenize(dialog.lower())))

        # builds mapping of tokens to int IDs
        dictionary = gensim.corpora.Dictionary(texts)

        # convert all tokens to IDs
        corpus = [dictionary.doc2bow(text) for text in texts]

        # build TFIDF model
        # https://en.wikipedia.org/wiki/Tf%E2%80%93idf
        # https://stackoverflow.com/questions/6255835/cosine-similarity-and-tf-idf
        tfidf = models.TfidfModel(corpus)
        index = similarities.SparseMatrixSimilarity(tfidf[corpus], num_features=dictionary.num_nnz)

        # run spacy on dialogs
        # spacy_dialogs = [nlp(dialog) for dialog in entry.dialog]

        print('Entry : ' + str(i + start))
        for j in range(0, 5):
            with open('graphs/graph' + str(j) + '.txt', 'r') as csv_file:
                ere_count = 0
                ere_guesses = Counter()
                sentence_count, sentence_correct, unmatched_sentences = 0, 0.0, 0
                for ere in csv_file:
                    ere_num = ere.split(',')[0]

                    if (str(sentence_count) != ere_num):  # done evaluating eres for a sentence
                        # sentence has no matches
                        if (str(sentence_count) not in entry.summary_to_dialog[1]):
                            sentence_count += 1
                            unmatched_sentences += 1
                        elif (ere_count > 0):
                            # calc label score/ label order score
                            s1_s2_label_values, s1_s2_order_values = calc_labels(
                                entry)
                            for k in range(0, len(s1_s2_label_values)):
                                ere_guesses[k] += (s1_s2_label_values[k] + s1_s2_order_values[k])

                            sentence_count, sentence_correct, random_correct = check_correct(
                                entry, ere_guesses, sentence_count, sentence_correct, random_correct)
                            ere_count = 0

                    # make flat list of tokens from ere
                    text = ere.split(',')[1:]
                    tokens = [word_tokenize(str_.lower()) for str_ in text]
                    tokens = [t for list_ in tokens for t in list_]

                    # calc spacy raw string compare
                    spacy_vals = [0] * len(entry.dialog)
                    # sen_nlp = nlp(entry.summaries_sentences[j][int(ere_num)])
                    # for k, dialog in enumerate(entry.dialog):
                    #     spacy_vals[k] = sen_nlp.similarity(spacy_dialogs[k])

                    # calc tfidf score
                    sentence_vec = dictionary.doc2bow(tokens)
                    sims = index[tfidf[sentence_vec]]
                    largest = 1 if max(sims) == 0 else max(sims)
                    tfidf_vals = [val / largest for val in sims]

                    # calc rarewords score
                    rarewords_values = [0] * len(entry.dialog)
                    sentence_rares = set()
                    for t in tokens:
                        if t in rarewords:
                            sentence_rares.add(t)
                    for k, dialog in enumerate(texts):
                        for token in dialog:
                            if token in sentence_rares:
                                rarewords_values[k] += 1
                    largest = 1 if max(rarewords_values) == 0 else max(rarewords_values)
                    rarewords_values = [val / largest for val in rarewords_values]

                    guess = make_ere_guess(tfidf_vals, rarewords_values, spacy_vals)
                    ere_guesses[str(guess)] += 5
                    ere_count += 1
                else:
                    # sentence has no matches
                    if (str(sentence_count) not in entry.summary_to_dialog[1]):
                        sentence_count += 1
                        unmatched_sentences += 1
                    elif (ere_count > 0):
                        s1_s2_label_values, s1_s2_order_values = calc_labels(
                            entry)
                        for k in range(0, len(s1_s2_label_values)):
                            ere_guesses[k] += (s1_s2_label_values[k] + s1_s2_order_values[k])

                        sentence_count, sentence_correct, random_correct = check_correct(
                            entry, ere_guesses, sentence_count, sentence_correct, random_correct)
                        ere_count = 0

                # print results for single summary
                sentence_count -= unmatched_sentences
                percent = float('nan') if sentence_count == 0 else sentence_correct/sentence_count
                print('summary: ' + str(j) + ' count:' + str(sentence_count) + ' correct:' +
                      str(sentence_correct) + ' percent:' + str(percent))

                total_evaluated += sentence_count
                total_correct += sentence_correct

    print('--------------TOTAL RESULTS-------------')
    print('count:' + str(total_evaluated) + ' correct:' +
          str(total_correct) + ' percent:' + str(total_correct/total_evaluated) + ' random: ' + str(random_correct/total_evaluated))


def calc_labels(entry):
    """ Calc score based on label appearence order and counts """
    # calc label score/ label order score
    s1_count, s1_first = 0, 0
    s1_s2_label_values, s1_s2_order_values = [0] * len(entry.dialog), [0] * len(entry.dialog)

    for t in word_tokenize(entry.summaries[0].lower()):
        if t == 's1':
            s1_count += 1
            if (s1_first == 0):
                s1_first = 1
        elif t == 's2':
            s1_count -= 1
            if (s1_first == 0):
                s1_first = -1

    # assign weights
    if (s1_count > 0):
        s1_s2_label_values = [1 if k % 2 == 0 else 0 for k in range(0, len(entry.dialog))]
    elif (s1_count < 0):
        s1_s2_label_values = [1 if k % 2 == 1 else 0 for k in range(0, len(entry.dialog))]
    if (s1_first == 1):
        s1_s2_order_values = [1 if k % 2 == 0 else 0 for k in range(0, len(entry.dialog))]
    elif (s1_first == -1):
        s1_s2_order_values = [1 if k % 2 == 1 else 0 for k in range(0, len(entry.dialog))]
    return s1_s2_label_values, s1_s2_order_values


def make_ere_guess(tfidf_values, rarewords_values, spacy_vals):
    """ Make guess for given ere bassed on input and method weights"""
    guesses = [0] * len(tfidf_values)
    for i in range(0, len(guesses)):
        guesses[i] += .2 * rarewords_values[i]
        guesses[i] += .8 * tfidf_values[i]
        guesses[i] += 0 * spacy_vals[i]

    return guesses.index(max(guesses))


def check_correct(entry, ere_guesses, sentence_count, sentence_correct, random_correct):
    """ Checks if a sentence was correctly matched to the appropriate dialog """

    correct_dialog = entry.summary_to_dialog[1][str(sentence_count)]
    most_common = ere_guesses.most_common()
    highest_matched = most_common[0]
    sentence_count += 1

    if (highest_matched[0] in correct_dialog):
        sentence_correct += 1
    else:
        tied = 0
        correct = 0

        while(tied < len(most_common) and most_common[tied][1] == highest_matched[1]):
            if (most_common[tied][0] in correct_dialog):
                correct += 1
            tied += 1
        if (correct > 0):
            sentence_correct += correct / tied

    random_correct += len(correct_dialog) / len(entry.dialog)

    return sentence_count, sentence_correct, random_correct


if (__name__ == '__main__'):
    if (len(sys.argv) != 3):
        print("Please run command with desired conversation/summary range ID, EX: 'py evalaute.py 0 44'")
    elif (int(sys.argv[1]) < 0 or int(sys.argv[1]) > 45 or int(sys.argv[2]) < 0 or int(sys.argv[2]) > 45):
        print("Argument/s out of range (0,45)")
    else:
        data = parse.parse()
        evaluate(data, calc_rarewords(data), int(sys.argv[1]), int(sys.argv[2]))
