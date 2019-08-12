import csv
import matplotlib.pyplot as plt
import argparse

parser = argparse.ArgumentParser(description='Plotting Reward')
parser.add_argument('--load_level', action="store_true", help='Shows markers of different load levels')
args = parser.parse_args()

if args.load_level:
    # read Out Mininet
    mininetTimeStampLoadList = []
    mininetLoadList = []
    with open('logs/timestamp_changing_load_levels_mininet.csv') as csvfile:
        reader = csv.reader(csvfile, delimiter= ',')
        for row in reader:
            if '#' not in row[0]:
                mininetTimeStampLoadList.append(row[1])
                mininetLoadList.append(row[0])
    timeStampRowIterator = 0
    verticalLineList = []

rewardList = []
stepList = []
# read out reward
with open('logs/reward_controller.csv') as csvfile:
    reader = csv.reader(csvfile, delimiter= ',')
    rowIterator = 0
    for row in reader:
        if '#' not in row[0]:
            if int(row[0]) < 5000:
                rewardList.append(float(row[1]))
                stepList.append(int(row[0]))
                if args.load_level:
                    time = row[2]
                    if timeStampRowIterator < len(mininetLoadList):
                        if time > mininetTimeStampLoadList[timeStampRowIterator]:
                            verticalLineList.append((int(row[0]), mininetLoadList[timeStampRowIterator]))
                            timeStampRowIterator += 1
                        rowIterator += 1
            else:
                break

if args.load_level:
    print(verticalLineList)
    for verticalLine in verticalLineList:
        plt.axvline(verticalLine[0], color='g')
        if(int(verticalLine[1]) > 1):
            plt.text(verticalLine[0] + 1, -13, s=str(verticalLine[1]), rotation=90)
        else:
            plt.text(verticalLine[0] + 1, -13, s='End', rotation=90)

plt.plot(stepList, rewardList)

plt.xlabel('Steps')
plt.ylabel('Reward')
#plt.savefig('reward.pdf')

plt.show()