### Controller

Contains the different instances of the controller:
remote controller - the ryu instance that gathers the network-metrics and procedures the rerouting
learning module - stats a process that communicates cia Pipe with the ryu-controller entity and performs the learning (Tabular)
functions - helper-functions
routingDFS - path search via Depth first search
config - change learning values
#### Folder description
/:
state space is only defined by the flow and their possible paths
/States_path_ids_flow_bw:
state space also contains bandwidth and includes that into learning