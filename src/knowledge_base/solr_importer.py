

def import_kb(cfg, solr):
    print('creating node index...')
    solr.create_core('kb_node', 'input_data/solr/kb_nodes')
    solr.import_csv('kb_node', cfg['kb_preprocessor']['output_dir_path'] + 'nodes.csv', 'node_id,node_text')

    print('creating edge type index...')
    solr.create_core('kb_edge_type', 'input_data/solr/kb_edge_type')
    solr.import_csv('kb_edge_type', cfg['kb_preprocessor']['output_dir_path'] + 'edge_type.csv', 'edge_type_id,edge_type_text')