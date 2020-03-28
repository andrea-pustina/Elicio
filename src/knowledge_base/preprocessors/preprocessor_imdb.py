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


def get_dict_value_by_key_substring(d, key_substring):
    for k, v in d.items():
        if key_substring in k:
            return v

    # print('{} not found in {}'.format(key_substring, d))
    return []


def preprocess_kb(cfg):
    groundtruth_path = cfg['preprocessor_imdb']['groundtruth_path']
    vertex_output_path = cfg['kb_preprocessor']['output_dir_path'] + 'nodes.csv'
    edge_output_path = cfg['kb_preprocessor']['output_dir_path'] + 'edges.csv'
    edge_type_output_path = cfg['kb_preprocessor']['output_dir_path'] + 'edge_type.csv'

    if not os.path.exists(os.path.dirname(vertex_output_path)):
        os.makedirs(os.path.dirname(vertex_output_path))

    with open(groundtruth_path, 'r', encoding="utf8") as groundtruth_file:
        with open(vertex_output_path, 'w', encoding="utf8") as vertex_out_file:
            with open(edge_output_path, 'w', encoding="utf8") as edge_out_file:
                with open(edge_type_output_path, 'w', encoding="utf8") as edge_type_out_file:

                    # used to make id unique
                    last_id_used = 0

                    groundtruth = json.load(groundtruth_file)
                    for groundtruth_data in groundtruth.values():
                        topic_entity = groundtruth_data['topic_entity_name'][0]
                        casts = get_dict_value_by_key_substring(groundtruth_data, 'Cast')
                        languages = get_dict_value_by_key_substring(groundtruth_data, 'Language')
                        durations = get_dict_value_by_key_substring(groundtruth_data, 'Runtime')
                        genres = get_dict_value_by_key_substring(groundtruth_data, 'Genre')
                        directors = get_dict_value_by_key_substring(groundtruth_data, 'Director')
                        writers = get_dict_value_by_key_substring(groundtruth_data, 'Writer')

                        last_id_used += 1
                        topic_id = last_id_used
                        vertex_out_file.write('{},"{}"\n'.format(topic_id, string_utils.clean_string(topic_entity)))

                        for cast in casts:
                            last_id_used += 1
                            vertex_out_file.write('{},"{}"\n'.format(last_id_used, string_utils.clean_string(cast)))
                            edge_out_file.write('{},{},{},"{}"\n'.format(topic_id, last_id_used, 1, 'cast'))

                        for language in languages:
                            last_id_used += 1
                            vertex_out_file.write('{},"{}"\n'.format(last_id_used, string_utils.clean_string(language)))
                            edge_out_file.write('{},{},{},"{}"\n'.format(topic_id, last_id_used, 2, 'language'))

                        for duration in durations:
                            last_id_used += 1
                            vertex_out_file.write('{},"{}"\n'.format(last_id_used, string_utils.clean_string(duration)))
                            edge_out_file.write('{},{},{},"{}"\n'.format(topic_id, last_id_used, 3, 'duration'))

                        for genre in genres:
                            last_id_used += 1
                            vertex_out_file.write('{},"{}"\n'.format(last_id_used, string_utils.clean_string(genre)))
                            edge_out_file.write('{},{},{},"{}"\n'.format(topic_id, last_id_used, 4, 'genre'))

                        for director in directors:
                            last_id_used += 1
                            vertex_out_file.write('{},"{}"\n'.format(last_id_used, string_utils.clean_string(director)))
                            edge_out_file.write('{},{},{},"{}"\n'.format(topic_id, last_id_used, 5, 'director'))

                        for writer in writers:
                            last_id_used += 1
                            vertex_out_file.write('{},"{}"\n'.format(last_id_used, string_utils.clean_string(writer)))
                            edge_out_file.write('{},{},{},"{}"\n'.format(topic_id, last_id_used, 6, 'writer'))

                    edge_type_out_file.write('{},"{}"\n'.format(1, 'cast'))
                    edge_type_out_file.write('{},"{}"\n'.format(2, 'language'))
                    edge_type_out_file.write('{},"{}"\n'.format(3, 'duration'))
                    edge_type_out_file.write('{},"{}"\n'.format(4, 'genre'))
                    edge_type_out_file.write('{},"{}"\n'.format(5, 'director'))
                    edge_type_out_file.write('{},"{}"\n'.format(6, 'writer'))
