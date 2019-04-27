import subprocess
import sys

import nltk
import spacy
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize

import depparser
import summ_depparser
import parse
from parse import Entry

stop_words = set(stopwords.words('english'))
nlp = spacy.load('en')  # requires you to run 'python -m spacy download en'


def build_KG(nltk_tree, graph_file, text_file, sentence_count=0):
    """ Takes a nltk.tree.Tree object and generates a GraphViz file """

    left = ''
    edge = ''
    for node in nltk_tree:
        if node.label() == 'NP':
            if left == '':
                left = '_'.join(token[0] for token in node)
            elif edge == '':
                left += '_'.join(token[0] for token in node)
            else:
                right = '_'.join(token[0] for token in node)
                write_triple(left, edge, right, graph_file, text_file, sentence_count)

                left = right
                edge = ''
        else:
            if edge == '':
                edge = '_'.join(token[0] for token in node)
            else:
                edge += '_'.join(token[0] for token in node)


def write_triple(left, edge, right, graph_file, text_file, sentence_num):
    """ Writes a node edge triple to the graphviz file"""

    # node_name [label="node name"]
    graph_file.write('"' + left +
                     '"' + ' [label="' + left.replace('_', ' ') + '"];\n')
    graph_file.write('"' + right.replace('/', '').replace('\\', '') +
                     '"' + ' [label="' + right.replace('_', ' ') + '"];\n')
    # node_1 -> node_2 [label="edge name"]
    graph_file.write('"' + left + '"' + ' -> '
                     + '"' + right + '"' + ' [label="' + edge.replace('_', ' ') + '"];\n')
    text_file.write(str(sentence_num) + ',' + left.replace('_', ' ') + ',' +
                    edge.replace('_', ' ') + ',' + right.replace('_', ' ') + '\n')


def generate_dot(list_, graph_file_path, text_file):
    """ Creates dot file for a single summary or conversation """

    with open(graph_file_path, 'w') as graph_file, open(text_file, 'w') as text_file:
        graph_file.write('digraph Summary {\n')
        sentence_dialog_count = 0
        for sentence_or_dialog in list_:
            doc = nlp(sentence_or_dialog)

            tokens = []
            for token in doc:
                tokens.append(token.text)

            text = nltk.pos_tag(tokens)
            tag_pattern = """NP: {<.*>+}
                                }(<DT|RB.*|TO>?<VB.*>+<DT|RB.*|TO>?)+{
                                VP: {(<DT|RB.*|TO>?<VB.*>+<DT|RB.*|TO>?)+}
                            """

            regexp_pattern = nltk.RegexpParser(tag_pattern)
            chunked = regexp_pattern.parse(text)
            build_KG(chunked, graph_file, text_file, sentence_dialog_count)
            # chunked.draw()

            sentence_dialog_count += 1

        graph_file.write('}')


def generate_kgs(id):
    """ Generates KGs using chinking/chunking """

    data = parse.parse()

    generate_dot(data[id].dialog, 'graphs/graph_convo.dot', 'graphs/graph_convo.txt')
    # requires ~graphviz-2.38\release\bin to be in PATH
    subprocess.run(['dot', '-Tpng', 'graphs/graph_convo.dot', '-o', 'graphs/graph_convo.png'])

    for count in range(0, 5):
        graph_name = 'graphs/graph' + str(count)

        # generate graphviz file
        generate_dot(data[id].summaries_sentences[count], graph_name + '.dot', graph_name + '.txt')

        # requires ~graphviz-2.38\release\bin to be in PATH
        subprocess.run(['dot', '-Tpng', graph_name + '.dot', '-o', graph_name + '.png'])


def generate_dot_depparser(list_, graph_file_path, text_file):
    """ Generates KGs using dependency parser """

    with open(graph_file_path, 'w') as graph_file, open(text_file, 'w') as text_file:
        graph_file.write('digraph Summary {\n')

        sentence_dialog_count = 0
        for dialog in list_:
            parsed = depparser.parse_dep(dialog)
            for eres in parsed:
                for ere in eres:
                    if (ere[0] is None and ere[2] is None):
                        write_triple("", ere[1], "", graph_file, text_file, sentence_dialog_count)
                    elif ere[0] is None:
                        write_triple("", ere[1], ere[2], graph_file,
                                     text_file, sentence_dialog_count)
                    elif ere[2] is None:
                        write_triple(ere[0], ere[1], "", graph_file,
                                     text_file, sentence_dialog_count)
                    else:
                        write_triple(ere[0], ere[1], ere[2], graph_file,
                                     text_file, sentence_dialog_count)
            sentence_dialog_count += 1

        graph_file.write('}')


def generate_dot_summdepparser(list_, graph_file_path, text_file):
    with open(graph_file_path, 'w') as graph_file, open(text_file, 'w') as text_file:
        graph_file.write('digraph Summary {\n')

        sentence_dialog_count = 0
        for summ in list_:
            parsed = summ_depparser.parse_summaries(summ)
            for eres in parsed:
                for ere in eres:
                    if (ere[0] is None and ere[2] is None):
                        write_triple("", ere[1], "", graph_file, text_file, sentence_dialog_count)
                    elif ere[0] is None:
                        write_triple("", ere[1], ere[2], graph_file,
                                     text_file, sentence_dialog_count)
                    elif ere[2] is None:
                        write_triple(ere[0], ere[1], "", graph_file,
                                     text_file, sentence_dialog_count)
                    else:
                        write_triple(ere[0], ere[1], ere[2], graph_file,
                                     text_file, sentence_dialog_count)
            sentence_dialog_count += 1

        graph_file.write('}')


def generate_kgs_depparser(id):
    data = parse.parse()

    generate_dot_depparser(data[id].dialog, 'graphs/graph_convo.dot', 'graphs/graph_convo.txt')
    # requires ~graphviz-2.38\release\bin to be in PATH
    subprocess.run(['dot', '-Tpng', 'graphs/graph_convo.dot', '-o', 'graphs/graph_convo.png'])

    for count in range(0, 5):
        graph_name = 'graphs/graph' + str(count)

        # generate graphviz file
        generate_dot_summdepparser(data[id].summaries_sentences[count],
                                   graph_name + '.dot', graph_name + '.txt')

        # requires ~graphviz-2.38\release\bin to be in PATH
        subprocess.run(['dot', '-Tpng', graph_name + '.dot', '-o', graph_name + '.png'])


if (__name__ == '__main__'):
    if (len(sys.argv) != 2):
        print("Please run command with desired conversation/summary ID, EX: 'py generatekgs.py 0'")
    elif (int(sys.argv[1]) < 0 or int(sys.argv[1]) > 44):
        print("Argument out of range (0,44)")
    else:
        generate_kgs(int(sys.argv[1]))
