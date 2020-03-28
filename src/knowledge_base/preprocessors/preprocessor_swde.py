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
    -edge_type
        edge_type_id
        edge_type_text

"""


def preprocess_kb(cfg):
    groundtruth_path = cfg['preprocessor_swde']['groundtruth_path']
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
                last_id_used = 0

                domains = cfg['preprocessor_swde']['domains']

                for domain in domains.keys():
                    domain_dir = groundtruth_path + domain
                    sites_annotation_files_paths = file.get_files_into_dir(domain_dir, full_path=True)

                    # get only site selected in config (for that domain)
                    site_annotation_files_paths = list(filter(lambda file_path: any(cfg_site in file_path for cfg_site in cfg['preprocessor_swde']['sites']), sites_annotation_files_paths))

                    main_annotation = domains[domain]

                    # id_map = {id_in_swde: id_in_kb}
                    id_map = {}

                    for site_annotation_path in site_annotation_files_paths:
                        if main_annotation in site_annotation_path:                                             # this is domain main annotation file (exfor movie is title)
                            with open(site_annotation_path, 'rU', encoding="utf8") as site_annotation_file:
                                site_annotation_file.readline()
                                site_annotation_file.readline()
                                for in_line in site_annotation_file:
                                    vertex = in_line.split('\t')

                                    vertex_swde_id = int(vertex[0])
                                    if vertex_swde_id not in id_map:
                                        id_map[vertex_swde_id] = last_id_used
                                        last_id_used += 1
                                    vertex_kb_id = id_map[vertex_swde_id]

                                    vertex_text = vertex[2]
                                    vertex_text_clean = string_utils.clean_string(vertex_text)

                                    vertex_out_file.write('{},"{}"\n'.format(vertex_kb_id, vertex_text_clean))

                        else:                                                                                    # this is NOT domain main annotation file (ex for movie is diretor)
                            # get annotation type (phone, director, ...)
                            annotation_type = site_annotation_path.split('-')[-1][:-4]

                            # get annotation type id
                            if annotation_type not in annotation_types_ids:
                                annotation_types_ids[annotation_type] = curr_annotation_type_id
                                curr_annotation_type_id += 1
                            annotation_type_id = annotation_types_ids[annotation_type]

                            with open(site_annotation_path, 'rU', encoding="utf8") as site_annotation_file:
                                site_annotation_file.readline()
                                site_annotation_file.readline()
                                for in_line in site_annotation_file:
                                    edge = in_line.split('\t')

                                    edge_src_swde_id = int(edge[0])
                                    if edge_src_swde_id not in id_map:
                                        id_map[edge_src_swde_id] = last_id_used
                                        last_id_used += 1
                                    edge_src_kb_id = id_map[edge_src_swde_id]

                                    edge_dst_kb_id = last_id_used
                                    last_id_used += 1

                                    edge_dst_text = edge[2]
                                    edge_dst_text_clean = string_utils.clean_string(edge_dst_text)

                                    vertex_out_file.write('{},"{}"\n'.format(edge_dst_kb_id, edge_dst_text_clean))
                                    edge_out_file.write('{},{},{},"{}"\n'.format(edge_src_kb_id, edge_dst_kb_id, annotation_type_id, annotation_type))

                for edge_type_text, edge_type_id in annotation_types_ids.items():
                    edge_type_out_file.write('{},"{}"\n'.format(edge_type_id, edge_type_text))