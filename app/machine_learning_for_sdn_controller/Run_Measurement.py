import subprocess
import argparse


parser = argparse.ArgumentParser(description='Starting Scenario')
parser.add_argument('--mn_file', default= 'Four_switches_two_ways.py', type=str, help='Give path to desired MininetFile, example: Mininet/Four_switches_two_ways.py')
args = parser.parse_args()

subprocess.Popen(['xterm', '-hold', '-e',  'ryu-manager remote_controller.py'])
p = subprocess.Popen(['xterm', '-hold', '-e', 'python3 {}'.format(args.mn_file)])
p.communicate()
subprocess.Popen(['mn', '-c'])