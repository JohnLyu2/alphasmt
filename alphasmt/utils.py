def solvedNumReward(resLst):
    return len([res for res in resLst if res[0]])/len(resLst)

def parNReward(resLst, n, timeout):
    parN = 0
    for i in range(len(resLst)):
        if not resLst[i][0]:
              parN += n * timeout
        else:
              parN += resLst[i][1]
    maxParN = len(resLst) * timeout * n
    return 1 - parN / maxParN