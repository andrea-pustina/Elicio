import os
import src.utils.string_utils as string_utils
import src.utils.elapsed_timer as Timer
import src.utils.files as file


"""
clean_kb creates 2 file:
    -vertices.csv
        vertex_id
        vertex_text
    -edges.csv
        source_vertex_id
        dest_vertex_id
        edge_type_id
        edge_type_text

"""


def load_edge_text(cfg, header):
    input_path = cfg['preprocessor_freebase_exq']['edges_text_input_path']
    output_path = cfg['kb_preprocessor']['output_dir_path'] + 'edge_type.csv'
    edge_texts = {}

    with open(output_path, 'w', encoding="utf8") as out_file:
        with open(input_path, 'rU', encoding="utf8") as in_file:
            if header:
                out_file.write('edge_type_id,edge_type_text\n')

            for in_line in in_file:
                edge = in_line.split('\t', 3)
                edge_type_id = edge[0]
                edge_type_text = string_utils.clean_string(edge[3][1:-2])

                out_file.write('{},"{}"\n'.format(edge_type_id, edge_type_text))
                edge_texts[edge_type_id] = string_utils.clean_string(edge_type_text)

    return edge_texts


def clean_vertices(cfg, header, drop_empty_nodes):
    input_path = cfg['preprocessor_freebase_exq']['vertices_input_path']
    output_path = cfg['kb_preprocessor']['output_dir_path'] + 'nodes.csv'

    n_vertex = file.count_lines(input_path)
    print('      total: {}'.format(n_vertex))

    if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))

    with open(output_path, 'w', encoding="utf8") as out_file:
        with open(input_path, 'rU', encoding="utf8") as in_file:
            if header:
                out_file.write('node_id,node_text\n')

            status_printer = Timer.StatusPrinter(n_vertex, padding='      ')
            for in_line in in_file:
                vertex = in_line.split('\t', 3)
                vertex_id = vertex[0]
                vertex_text = string_utils.clean_string(vertex[3][1:-2])

                if drop_empty_nodes and vertex_text is "":
                    continue

                out_file.write('{},"{}"\n'.format(vertex_id, vertex_text))

                status_printer.operation_done()
            status_printer.finish()


def clean_edges(cfg, header):
    input_path = cfg['preprocessor_freebase_exq']['edges_input_path']
    output_path = cfg['kb_preprocessor']['output_dir_path'] + 'edges.csv'
    edge_texts = load_edge_text(cfg, header)

    n_edges = file.count_lines(input_path)
    print('      total: {}'.format(n_edges))

    if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))

    with open(output_path, 'w', encoding="utf8") as out_file:
        with open(input_path, 'rU', encoding="utf8") as in_file:
            if header:
                out_file.write('source_node_id,dest_node_id,edge_type_id,edge_type_text\n')

            status_printer = Timer.StatusPrinter(n_edges, padding='      ')
            for in_line in in_file:
                edge = in_line.split(' ')
                source_id = edge[0]
                dest_id = edge[1]
                edge_id = edge[2][0:-1]
                edge_text = edge_texts[edge_id]

                out_file.write('{},{},{},"{}"\n'.format(source_id, dest_id, edge_id, edge_text))

                status_printer.operation_done()
            status_printer.finish()


def preprocess_kb(cfg, header, drop_empty_nodes):
    timer = Timer.Timer()
    print('start clean kb...\n   clean vertices...')
    print("      " + timer.start())
    clean_vertices(cfg, header, drop_empty_nodes)
    print("      " + timer.stop())
    print('   clean edges...')
    print("      " + timer.start())
    clean_edges(cfg, header)
    print("      " + timer.stop())
    print('   finish')