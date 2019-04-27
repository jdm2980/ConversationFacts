""" Tests the graphviz dependency """

import subprocess

GRAPH_FILE_PATH = 'graphs/test.dot'
GRAPH_IMAGE_PATH = 'graphs/test.png'

try:
    # generate test graphviz file
    with open(GRAPH_FILE_PATH, 'w') as graph_file:
        graph_file.write('digraph Summary {\n')
        graph_file.write('Test1 [label="Node 1"];\n')
        graph_file.write('Test2 [label="Node 2"];\n')
        graph_file.write('Test1 -> Test2 [label="edge"];\n')
        graph_file.write('}')

    # requires ~graphviz-2.38\release\bin to be in PATH
    subprocess.run(['dot', '-Tpng', GRAPH_FILE_PATH, '-o', GRAPH_IMAGE_PATH])
    print("GraphViz succesfully worked!")
except:
    print("GraphViz execution failed.")