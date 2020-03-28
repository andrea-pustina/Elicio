import json
import urllib.parse
import src.utils.files as file_util
from urllib.request import urlopen
import src.utils.docker as docker
import src.utils.shell as shell
import http.client


class Solr:
    def __init__(self, cfg):
        self.host = cfg['solr']['host']

    def get_core_list(self):
        cmd = 'admin/cores?action=STATUS'
        response = self.send_command(cmd)
        return list(response['status'].keys())

    def send_command(self, cmd):
        connection = urlopen(self.host + cmd + '&wt=json')
        response = json.load(connection)
        return response

    def delete_core(self, core_name):
        cmd = 'admin/cores?action=UNLOAD&core={}&deleteIndex=true&deleteDataDir=true'.format(core_name)
        response = self.send_command(cmd)
        return response

    def create_core(self, core_name, core_conf_dir_path):
        print('create solr core...')

        if core_name in self.get_core_list():
            print('   core already exists, deleting... ', end='')
            self.delete_core(core_name)
            print('done\n   start creating... ', end='')

        conf_volume_path = 'generated_data/docker/solr/data/' + core_name
        conf_volume_path_into_container = '/opt/solr/server/solr/mycores/'
        core_conf_container_path = conf_volume_path_into_container + core_name

        docker.unblock_docker_volume(conf_volume_path_into_container, 'solr', './docker')
        file_util.create_dir(conf_volume_path)
        file_util.copy_and_overwrite_dir(core_conf_dir_path, conf_volume_path)
        docker.unblock_docker_volume(conf_volume_path_into_container, 'solr', './docker')

        cmd = 'admin/cores?action=CREATE&name={}&instanceDir={}&config=solrconfig.xml&dataDir=data'.format(core_name, core_conf_container_path)
        response = self.send_command(cmd)
        print('done')

    def send_query(self, core, query, start_row=0, end_row=10000):
        query = urllib.parse.quote(query, safe='')
        response = self.send_command('{}/select?q={}&rows={}&start={}'.format(core, query, end_row, start_row))
        return response['response']['docs']

    def add_doc(self, core, doc):
        connection = http.client.HTTPConnection("localhost", 8983)
        headers = {'Content-type': 'application/json'}

        request = {'add': {'doc': doc, 'boost': 1, 'overwrite': True, 'commitWithin': 1}}
        json_request = json.dumps(request)

        connection.request('POST', '/solr/{}/update?wt=json&commit=true'.format(core), json_request, headers)

        response = connection.getresponse()
        #print(response.read().decode())

    @staticmethod
    def import_csv(core_name, csv_path, csv_header):
        print('import solr data...')
        shell.execute_cmd_shell("curl 'http://localhost:8983/solr/{}/update?commit=true&header=false&fieldnames={}' --data-binary @{} -H 'Content-type:application/csv'".format(core_name, csv_header, csv_path))
        print('   done')
