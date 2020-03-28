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


def clean_edge_text(cfg, header):
    input_path = cfg['preprocessor_freebase_easy']['edges_input_path']
    output_path = cfg['kb_preprocessor']['output_dir_path'] + 'edge_type.csv'
    edge_texts = {}

    n_edges = file.count_lines(input_path)

    with open(output_path, 'w', encoding="utf8") as out_file:
        with open(input_path, 'rU', encoding="utf8") as in_file:
            if header:
                out_file.write('edge_type_id,edge_type_text\n')

            status_printer = Timer.StatusPrinter(n_edges, padding='      ')
            for in_line in in_file:
                edge = in_line.split('\t')
                edge_text = edge[1]
                edge_id = string_utils.hash_string(edge_text)

                edge_text_clean = string_utils.clean_string(edge_text)

                if edge_id not in edge_texts:
                    out_file.write('{},"{}"\n'.format(edge_id, edge_text_clean))
                    edge_texts[edge_id] = string_utils.clean_string(edge_text_clean)

                status_printer.operation_done()
            status_printer.finish()

        print('      total relation type: {}'.format(len(edge_texts)))

    return edge_texts


def clean_vertices(cfg, header, drop_empty_nodes):
    input_path = cfg['preprocessor_freebase_easy']['vertices_input_path']
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
                vertex = in_line.split('\t')
                vertex_text = vertex[0]
                vertex_id = string_utils.hash_string(vertex_text)

                vertex_text_clean = string_utils.clean_string(vertex_text)

                if drop_empty_nodes and vertex_text is "":
                    continue

                out_file.write('{},"{}"\n'.format(vertex_id, vertex_text_clean))

                status_printer.operation_done()
            status_printer.finish()


def clean_edges(cfg, header):
    input_path = cfg['preprocessor_freebase_easy']['edges_input_path']
    output_path = cfg['kb_preprocessor']['output_dir_path'] + 'edges.csv'

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
                edge = in_line.split('\t')
                source_text = edge[0]
                edge_text = edge[1]
                dest_text = edge[2]

                source_id = string_utils.hash_string(source_text)
                edge_id = string_utils.hash_string(edge_text)
                dest_id = string_utils.hash_string(dest_text)

                edge_text_clean = string_utils.clean_string(edge_text)

                out_file.write('{},{},{},"{}"\n'.format(source_id, dest_id, edge_id, edge_text_clean))

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

    print('   clean edges type...')
    print("      " + timer.start())
    clean_edge_text(cfg, header)
    print("      " + timer.stop())

    print('   finish')