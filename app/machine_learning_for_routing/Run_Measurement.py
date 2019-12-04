import subprocess
import argparse


def main(mn_file="Four_switches_two_ways.py"):
    subprocess.Popen(['xterm', '-hold', '-e', 'python {}'.format(mn_file)])
    subprocess.Popen(['xterm', '-hold', '-e', 'ryu-manager remote_controller.py'])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mn', help='Specify the desired topology/scenario')
    args = parser.parse_args()

    if args.mn:
        main(args.mn)
    else:
        main()
