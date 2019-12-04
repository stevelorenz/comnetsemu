import csv
import matplotlib.pyplot as plt

# read Out Mininet
mininetTimeStampLoadList = []
mininetLoadList = []
with open('reward_mininet.csv') as csvfile:
    reader = csv.reader(csvfile, delimiter= ',')
    for row in reader:
        mininetTimeStampLoadList.append(row[2])
        mininetLoadList.append(row[1])

rewardController = []
epochReward = []
# read out reward
with open('reward_controller.csv') as csvfile:
    reader = csv.reader(csvfile, delimiter= ',')
    for row in reader:
        rewardController.append(float(row[1]))
        epochReward.append(int(row[0]))
print(epochReward)
#newList = [i for e, i in enumerate(epochReward) if e % 20 == 0]
print(len(epochReward))
#print(len(newList))
plt.plot(epochReward, rewardController)
plt.show()
