import json
import math
import matplotlib.pyplot as plt

def openQ():
    with open('Q_array_save_2.json') as file:
        q = json.load(file)  # use `json.loads` to do the reverse
        #print(q)
    return q
qList = openQ()
rwrdList = []
x=[]
print(qList[-1])
# Q , savingIterator, averageReward
for lolQ in qList:
    #print("Average reward: {}".format(lolQ[2]))
    rwrdList.append(lolQ[2])
    x.append(lolQ[1])
print(len(qList))
print(max(rwrdList))
print(rwrdList)
print(qList[-1][0])
plt.plot(x, rwrdList)
plt.show()