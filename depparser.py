""" Creates the ERE triples for conversation dialog using the dependency tree """

import spacy

import parse
from parse import Entry

nlp = spacy.load("en")


def process_root(root, children):
    """ Processes the root of the dialog, collecting any necessary children. This forms the relation for the ERE """

    rel = root.text
    dependencies = ["neg", "prt"] # Wanted children
    for child in children:
        if child.dep_ in dependencies:
            if child.i < root.i:
                rel = child.text + " " + rel
            else:
                rel = rel + " " + child.text
    return rel

def process_subtree(token, dependencies, entities):
    """ Processes a subtree of a token, it keeps all children that are in dependecies """    
    if token.dep_ in dependencies or (token.dep_ == 'det' and token.lower_ == 'no'):
        entities.append(token)

        for child in token.children: # Recursively call function on all valid children
            process_subtree(child, dependencies, entities)
    return entities

def process_root_subj(root, children):
    """ Process a subject off of the root """
    entities = [root]

    # Desired dependencies for subtree
    subtree_dependencies = ["prep","pobj","dobj","csubj","nsubj","xsubj","compound","nsubjpass","oprd","relcl"]

    # Call process subtree on all children
    for child in children:
        entities = process_subtree(child, subtree_dependencies, entities)

    # Join the final entities in the order they show up in the string
    final_entities = sorted(entities, key=lambda k: k.i)
    return ' '.join([entity.text for entity in final_entities])

def process_conjuctions(root, children):
    """ Process a conjuction that is within a component """
    conj_entities = []

    conj_dependencies = ["conj"]
    
    # Desired dependencies for subtree
    subtree_dependencies = ["prep","pobj","dobj","csubj","nsubj","xsubj","relcl","amod","prt","neg","compound","nsubjpass","oprd","relcl"]
    for child in children:
        if child.dep_ in conj_dependencies: # If child is a conjuction, process the subtree 
            entities = [child]
            for c in child.children:
                entities = process_subtree(c, subtree_dependencies, entities)
            final_entities = sorted(entities, key=lambda k: k.i)
            conj_entities.append(' '.join([entity.text for entity in final_entities]))
    return conj_entities

def process_root_comp(root, children):
    """ Process a component off of the root """
    entities = [root]
    
    # Desired dependencies for subtree
    subtree_dependencies = ["prep","pobj","dobj","csubj","nsubj","xsubj","advmod","pcomp","ccomp","neg","poss","compound","amod","nsubjpass","oprd","relcl"]
    
    # Process each child as a subtree
    for child in children: 
        entities = process_subtree(child, subtree_dependencies, entities)
    
    # Join the final entities in the order they show up in the string
    final_entities = sorted(entities, key=lambda k: k.i)
    return ' '.join([entity.text for entity in final_entities])

def process_new_entity(root, children):
    """ Process a conjunction that comes off of the original ROOT, this forms a new ERE """
    ret = []

    # Get the root 
    rel = process_root(root, children)
    if len(children) == 0:
        return []

    subj_dependencies = ["csubj","nsubj","xsubj","nsubjpass"]
    comp_dependencies = ["ccomp","xcomp","acomp","dobj","pobj","prep","pcomp"]
    conj_dependencies = ["conj","advcl"]
    subj_entity = None
    comp_entity = None
    conj_entities = []
    new_eres = []
    for child in children:
        if child.dep_ in subj_dependencies: # Process the subject
            subj_entity = process_root_subj(child, [c for c in child.children])
        if child.dep_ in comp_dependencies: # Process the component
            comp_entity = process_root_comp(child, [c for c in child.children])
            conj_entities = conj_entities + process_conjuctions(child, [c for c in child.children])
        if child.dep_ in conj_dependencies: # Process any conjunctions
            new_eres = new_eres + process_new_entity(child, [c for c in child.children])

            #If conjunctions have no subject, inherit it
            for idx, ere in enumerate(new_eres):
                if ere[0] == None:
                    temp = new_eres.pop(idx)
                    new_eres.append( (subj_entity, temp[1], temp[2]) )
    
    # Join all new EREs in a list
    ret.append( (subj_entity,rel,comp_entity) )
    for ent in conj_entities:
        ret.append( (subj_entity,rel,ent) )
    for ere in new_eres:
        ret.append(ere)
    return ret
    
def parse_dep(dialog):
    """ Find the EREs for the given dialog """
    fin = []

    # Loop over each sentence
    for sent in dialog.split('.'):
        doc = nlp(sent)

        # Find the root
        root = None
        for token in doc:
            if token.dep_ == 'ROOT':
                root = token
        if root == None:
            break

        children = [child for child in root.children]
        rel = process_root(root, children)

        subj_dependencies = ["csubj","nsubj","xsubj","nsubjpass"]
        comp_dependencies = ["ccomp","xcomp","acomp","dobj","pobj", "prep","pcomp"]
        conj_dependencies = ["conj","advcl"]
        ret = []
        subj_entity = None
        comp_entity = None
        conj_entities = []
        new_eres = []

        for child in children:
            if child.dep_ in subj_dependencies: # Process the subject
                subj_entity = process_root_subj(child, [c for c in child.children])
            if child.dep_ in comp_dependencies: # Process the component
                comp_entity = process_root_comp(child, [c for c in child.children])
                conj_entities = conj_entities + process_conjuctions(child, [c for c in child.children])
            if child.dep_ in conj_dependencies: # Process conjunctions
                new_eres = new_eres + process_new_entity(child, [c for c in child.children])
                
                #If conjunctions have no subject, inherit it
                for idx, ere in enumerate(new_eres):
                    if ere[0] == None:
                        temp = new_eres.pop(idx)
                        new_eres.append( (subj_entity, temp[1], temp[2]) )

        # Join all of the EREs
        ret.append( (subj_entity,rel,comp_entity) )
        for ent in conj_entities:
            ret.append( (subj_entity,rel,ent) )
        for ere in new_eres:
            ret.append(ere)
        fin.append(ret)
    return fin
        
if __name__ == '__main__':
    import sys
    import parse
    data = parse.parse()

    if len(sys.argv) != 2:
        print("Please run command with desired conversation/summary ID, EX: 'py depparse.py 0'")
    elif not int(sys.argv[1]) in range(0,45):
        print("Error with given argument")
    else:
        id = int(sys.argv[1])
        flag = True
        for dialog in data[id].dialog:
            if flag:
                print("S1: " + dialog)
                print("EREs: " + str(parse_dep(dialog)))
            else:
                print("S2: " + dialog)
                print("EREs: " + str(parse_dep(dialog)))
            flag = not flag
            print("\n")
