import os
import src.utils.string_utils as string_utils
import src.utils.elapsed_timer as Timer
import src.utils.files as file
import json


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
    -edge_type
        edge_type_id
        edge_type_text

"""


def preprocess_kb(cfg):
    groundtruth_path = 'input_data/monitor_dataset/www.getprice.com.au'
    vertex_output_path = cfg['kb_preprocessor']['output_dir_path'] + 'nodes.csv'
    edge_output_path = cfg['kb_preprocessor']['output_dir_path'] + 'edges.csv'
    edge_type_output_path = cfg['kb_preprocessor']['output_dir_path'] + 'edge_type.csv'


    if not os.path.exists(os.path.dirname(vertex_output_path)):
        os.makedirs(os.path.dirname(vertex_output_path))

    with open(vertex_output_path, 'w', encoding="utf8") as vertex_out_file:
        with open(edge_output_path, 'w', encoding="utf8") as edge_out_file:
            with open(edge_type_output_path, 'w', encoding="utf8") as edge_type_out_file:

                # annotation type is edge type (director, writer, ...)
                annotation_types_ids = {}
                curr_annotation_type_id = 0

                # used to make id unique
                last_id = 0

                groundtruth_files = file.get_files_into_dir(groundtruth_path, full_path=True)
                groundtruth_files = list(filter(lambda x: '.json' in x, groundtruth_files))

                # id_map = {id_in_dataset: id_in_kb}
                id_map = {}

                for groundtruth_file_path in groundtruth_files:

                    with open(groundtruth_file_path, 'rU', encoding="utf8") as grountruth_file:
                        file_groundtruth = json.loads(grountruth_file.read())

                        page_topic_text = file_groundtruth['<page title>'].replace(' | Compare Prices & Save shopping in Australia', '').split(' ')[1]
                        page_topic_text = string_utils.clean_string(page_topic_text)
                        page_topic_id = last_id
                        last_id += 1
                        vertex_out_file.write('{},"{}"\n'.format(page_topic_id, page_topic_text))

                        for edge_type_text, obj_text in file_groundtruth.items():
                            if edge_type_text == '<page title>':
                                continue

                            # get annotation type id
                            if edge_type_text not in annotation_types_ids:
                                annotation_types_ids[edge_type_text] = curr_annotation_type_id
                                curr_annotation_type_id += 1
                            edge_type_id = annotation_types_ids[edge_type_text]

                            obj_id = last_id
                            last_id += 1

                            obj_text_clean = string_utils.clean_string(obj_text)

                            vertex_out_file.write('{},"{}"\n'.format(obj_id, obj_text_clean))
                            edge_out_file.write('{},{},{},"{}"\n'.format(page_topic_id, obj_id, edge_type_id, edge_type_text))

                for edge_type_text, edge_type_id in annotation_types_ids.items():
                    edge_type_out_file.write('{},"{}"\n'.format(edge_type_id, edge_type_text))
