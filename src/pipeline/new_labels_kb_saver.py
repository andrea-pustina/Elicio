import src.utils.compressor as compressor
import src.utils.elapsed_timer as timer
import src.utils.string_utils as string_utils

def save_new_labels_in_kb(page_service, neo4j, solr, cfg):
    # add new labels to kb
    debug = cfg['save_new_labels_in_kb']['debug']
    print('adding new labels to kb...')

    max_edge_type_id = int(neo4j.get_max_edge_property_value('edge_type_id').single().value())
    new_labels_edge_type_id = max_edge_type_id + 1

    max_node_id = int(neo4j.get_max_node_property_value('node_id').single().value())

    if debug:
        print('   max_node_id: {}'.format(max_node_id))
        print('   new labels edge_type_id: {}'.format(new_labels_edge_type_id))

    total_operation_count = page_service.count_all()
    status_printer = timer.StatusPrinter(total_operation_count, padding='      ', avoid_use_of_timer=False)

    for webpage in page_service.get_all():
        if webpage['topic_id'] is None or 'new_labels' not in webpage:
            continue

        topic_id = webpage['topic_id']

        new_labels = webpage['new_labels']
        new_labels = [{'obj_text': new_label['obj_text'], 'pred_text': new_label['pred_text']} for new_label in
                      new_labels]

        page_entities = compressor.decompress_obj(webpage['page_entities'])
        topic_related_entities = page_entities[topic_id]['related_objs'].values()
        topic_related_entities = {entity['obj_text']: list(entity['rel_types'].values()) for entity in
                                  topic_related_entities}

        # filter only new labels that are not in the kb
        kb_new_labels = []
        for new_label in new_labels:
            new_label_obj = new_label['obj_text']
            new_label_pred = new_label['pred_text']

            if not new_label_obj in topic_related_entities or not any(
                    [new_label_pred == rel_type for rel_type in topic_related_entities[new_label_obj]]):
                # this is a new label (not in the knowledge base)
                kb_new_labels.append(new_label)

        # add new label to kb
        curr_new_node_id = max_node_id + 1
        for new_label in kb_new_labels:
            new_label_obj = new_label['obj_text']
            new_label_pred = new_label['pred_text']

            neo4j.create_node({'node_id': curr_new_node_id, 'node_text': new_label_obj})
            solr.add_doc('kb_node', {'node_id': curr_new_node_id, 'node_text': new_label_obj})


            solr_response = solr.send_query('kb_edge_type', 'edge_type_text:"{}"'.format(new_label_pred))
            #print("{} - {}".format(new_label_pred, solr_response))
            if len(solr_response)>0:
                edge_type_id = solr_response[0]['edge_type_id']
                edge_type_text = solr_response[0]['edge_type_text']
            else:
                edge_type_id = new_labels_edge_type_id
                edge_type_text = new_label_pred
                solr.add_doc('kb_edge_type', {'edge_type_id': edge_type_id, 'edge_type_text': edge_type_text})

                new_labels_edge_type_id += 1

            neo4j.create_edge(topic_id, curr_new_node_id, {'edge_type_id': edge_type_id, 'edge_type_text': edge_type_text})
            curr_new_node_id += 1

        if debug:
            print('   {} {}'.format(webpage['template'], webpage['file_name']))
            print('      topic_id: {}'.format(topic_id))
            print('      kb topic related entities: {}'.format(topic_related_entities))
            print('      new_labels_extracted: {}'.format(new_labels))
            print('      kb_new_labels: {}'.format(kb_new_labels))
        status_printer.operation_done()

    status_printer.finish()