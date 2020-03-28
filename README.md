Requirements:
    - chrome

Before first start (containers check):
    - cd ./docker
    - docker-compose up (run solr and neo4j containers)
    - check that containers start with no errors
    - docker compose down
    
Normal start:
    - Option_A (automatic docker management)
        - in config set manage_docker=true
        - run main.py
    - Option_B (manual docker management)
        - in config set manage_docker=false
        - cd ./docker
        - docker-compose up
N.B. to import_kb_graphdb and import_kb_solr start Option_A must be used.
N.B. usually I use Option_B because containers are not restarted every time main.py is launched
N.B. if there are "permission errors" -> sudo chmod -R 777 ./generated_data

Web Management Interfaces:
    - neo4j:   http://localhost:7474/   (user: neo4j, psw: test)
    - solr:    http://localhost:8983/
    - mongodb: http://localhost:8081/   (user: root, psw: example)
N.B in order to interfaces to be available -> cd ./docker; docker-compose up 
