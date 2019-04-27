""" Creates the ERE triples for summary text using the dependency tree """

import spacy
import re
import parse
from parse import Entry

nlp = spacy.load("en")

def process_root(root, children):
    """ Processes the root of the sentence, collecting any necessary children. This forms the relation for the ERE """


    rel = root.text
    dependencies = ["neg", "prt"] # Wanted children
    for child in children:
        if child.dep_ in dependencies:
            if child.i < root.i:
                rel = child.text + " " + rel
            else:
                rel = rel + " " + child.text
    return rel

def process_allsubtree(token, entities, conjunctions):
    """ Joins all children of a subtree into a entity """

    #TODO: Find proper list of desired children for summaries
    entities.append(token)
    for child in token.children:
        if child.dep_ not in ['conj', 'cc']:
            process_allsubtree(child, entities, conjunctions)
        elif child.dep_ in ['conj']:
            conjunctions.append(child)

    return (entities, conjunctions)

def get_entity_str(entities):
    """ Joins list of tokens as a string in the proper order """

    final_entities = sorted(entities, key=lambda k: k.i)
    return ' '.join([entity.text for entity in final_entities])

def dep_parse(root):
    """ Parse the given ROOT into EREs"""

    children = [child for child in root.children]
    rel = process_root(root, children)

    subj_dependencies = ["csubj","nsubj","xsubj","nsubjpass"]
    comp_dependencies = ["ccomp","xcomp","acomp","dobj","pobj", "prep","pcomp"]
    sentence_eres = []
    subj_entity = None
    comp_entity = None
    conj_entities = []
    for child in children:
        if child.dep_ in subj_dependencies: # Process subject
            (subj_entities, temp) = process_allsubtree(child, [],[])
            subj_entity = get_entity_str(subj_entities)
        if child.dep_ in comp_dependencies: # Process component
            (comp_entities, comp_conj) = process_allsubtree(child, [],[])
            comp_entity = get_entity_str(comp_entities)
            for conj in comp_conj:
                (temp, conj_temp) = process_allsubtree(conj, [],[])
                comp_conj = comp_conj + conj_temp
                conj_entities.append(get_entity_str(temp))
    
    # Form list of EREs
    sentence_eres.append( (subj_entity,rel,comp_entity) )
    for ent in conj_entities:
        sentence_eres.append( (subj_entity,rel,ent) )
    return sentence_eres


def parse_summaries(summary):
    """ Finds the EREs for each sentence in the given summary """

    summary_eres = []
    for sent in summary.split('.'):
        doc = nlp(sent)

        root = None
        for token in doc:
            if token.dep_ == 'ROOT':
                root = token
        if root == None:
            break

        summary_eres.append(dep_parse(root))
    return summary_eres

if __name__ == '__main__':
    import sys
    import parse
    data = parse.parse()

    if len(sys.argv) != 2:
        print("Please run command with desired conversation/summary ID, EX: 'py summ_depparse.py 0'")
    elif not int(sys.argv[1]) in range(0,45):
        print("Error with given argument")
    else:
        id = int(sys.argv[1])
        for summ in data[id].summaries:
            print("Summary:")
            print(summ)
            eres = parse_summaries(summ)
            print(eres)
            print("\n")