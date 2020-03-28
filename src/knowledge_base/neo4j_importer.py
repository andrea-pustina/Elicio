import src.utils.shell as shell


def create_header_files(cfg):
    nodes_header_file = cfg['kb_preprocessor']['output_dir_path'] + 'nodes_header.csv'
    edges_header_file = cfg['kb_preprocessor']['output_dir_path'] + 'edges_header.csv'

    with open(nodes_header_file, 'w', encoding="utf8") as out_file:
        out_file.write('node_id:ID(CommonNode),node_text\n')

    with open(edges_header_file, 'w', encoding="utf8") as out_file:
        out_file.write('source_id:START_ID(CommonNode),dest_id:END_ID(CommonNode),edge_type_id,edge_type_text\n')


def import_kb(cfg, neo4j):
    """
    clean_kb with header=False
    :param cfg:
    :param neo4j:
    :return:
    """

    if cfg['import_kb']['ssd_disk']:
        ssd_disk_string = 'true'
    else:
        ssd_disk_string = 'false'

    print('import kb:\n   create header files...')
    create_header_files(cfg)
    print('      done')

    print('   drop db...')
    shell.execute_cmd_shell('docker-compose exec -T neo4j rm -R /var/lib/neo4j/data/databases/graph.db', cwd='./docker')
    print('      done')

    print('   import data...')
    shell.execute_cmd_shell(
        'docker-compose exec -T neo4j /var/lib/neo4j/bin/neo4j-admin import --high-io={} --ignore-missing-nodes --id-type integer --nodes:CommonNode "import/knowledge_base/nodes_header.csv,import/knowledge_base/nodes.csv" --relationships:CommonRelation "import/knowledge_base/edges_header.csv,import/knowledge_base/edges.csv"'.format(ssd_disk_string),
        cwd='./docker')
    print('      done')


def import_kb_and_create_index(cfg, neo4j):
    import_kb(cfg, neo4j)

    if cfg['main']['manage_docker']:
        neo4j.restart_neo4j()
        neo4j.create_index('CommonNode', 'node_id', wait_finish=False)
        neo4j.create_index('CommonRelation', 'edge_type_id', wait_finish=False)