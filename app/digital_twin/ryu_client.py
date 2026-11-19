import requests
BASE = 'http://127.0.0.1:8080'

switches = requests.get(f'{BASE}/v1.0/topology/switches').json()
links    = requests.get(f'{BASE}/v1.0/topology/links').json()
hosts    = requests.get(f'{BASE}/v1.0/topology/hosts').json()
flows    = requests.get(f'{BASE}/stats/flow/1').json()   # dpid 1 = s1

switch_file = open("./ryu_output/switches.txt", "w")
links_file = open("./ryu_output/links.txt", "w")
hosts_file = open("./ryu_output/hosts.txt", "w")
flows_file = open("./ryu_output/flows.txt", "w")