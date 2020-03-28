import src.knowledge_base.preprocessors.preprocessor_freebase_easy as preprocessor_freebase_easy
import src.knowledge_base.preprocessors.preprocessor_freebase_exq as preprocessor_freebase_exq
import src.knowledge_base.preprocessors.preprocessor_swde as preprocessor_swde
import src.knowledge_base.preprocessors.preprocessor_imdb as preprocessor_imdb
import src.knowledge_base.preprocessors.preprocessor_monitor as preprocessor_monitor


def preprocess_kb(cfg):
    if cfg['import_kb']['kb_source'] == 'freebase_exq':
        preprocessor_freebase_exq.preprocess_kb(cfg, header=False, drop_empty_nodes=False)
    elif cfg['import_kb']['kb_source'] == 'freebase_easy':
        preprocessor_freebase_easy.preprocess_kb(cfg, header=False, drop_empty_nodes=False)
    elif cfg['import_kb']['kb_source'] == 'swde':
        preprocessor_swde.preprocess_kb(cfg)
    elif cfg['import_kb']['kb_source'] == 'monitor':
        preprocessor_monitor.preprocess_kb(cfg)
    elif cfg['import_kb']['kb_source'] == 'imdb':
        preprocessor_imdb.preprocess_kb(cfg)
