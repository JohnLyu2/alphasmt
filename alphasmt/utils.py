def solvedNum(resLst):
    return len([res for res in resLst if res[0]])

def solvedNumReward(resLst):
    return solvedNum(resLst)/len(resLst)

def parN(resLst, n, timeout):
    parN = 0
    for i in range(len(resLst)):
        if not resLst[i][0]:
              parN += n * timeout
        else:
              parN += resLst[i][1]
    return parN
    
def parNReward(resLst, n, timeout):
    par_n = parN(resLst, n, timeout)
    maxParN = len(resLst) * timeout * n
    return 1 - par_n / maxParN