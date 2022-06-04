from math import log, exp, sqrt
import numpy as np
import time
import multiprocessing

# arithmetic average call
# payoff = max(Save,τ − K, 0)

# time_elapsed ------> t
# time_left_to_Maturity ------> T - t
class Tree_Node:
    def __init__(self, time_elapsed, layers_prev, M, u, d, StInit, StAve, St, i, j, K):
        self.time_elapsed = time_elapsed
        self.layers_prev = layers_prev
        self.M = M
        self.u = u
        self.d = d
        self.StInit = StInit
        self.StAve = StAve
        self.St = St
        self.i = i+1
        self.j = j
        self.K = K

        self.avgMax = None
        self.avgMin = None
        self.avgLst = []
        self.callValue = []
        
    # calculate avgMax and avgMin
    def calc_Amax(self):
        if self.time_elapsed == 0:
            Amax = (self.StInit + self.StInit * self.u * (1-self.u**(self.i-self.j))/(1-self.u) + self.StInit * self.u**(self.i - self.j) * self.d * (1-self.d**self.j)/(1-self.d))/(self.i+1)
            self.avgMax = Amax
        else:
            Amax = (self.StAve*(self.layers_prev+1) + self.StInit * self.u * (1-self.u**(self.i-self.j))/(1-self.u) + self.StInit * self.u**(self.i - self.j) * self.d * (1-self.d**self.j)/(1-self.d))/(self.i+self.layers_prev+1)
            self.avgMax = Amax

    def calc_Amin(self):
        if self.time_elapsed == 0:
            Amin = (self.StInit + self.StInit * self.d * (1-self.d**self.j)/(1-self.d) + self.StInit * self.d**self.j * self.u * (1-self.u**(self.i - self.j))/(1-self.u))/(self.i+1)
            self.avgMin = Amin
        else:
            Amin = (self.StAve*(self.layers_prev+1) + self.StInit * self.d * (1-self.d**self.j)/(1-self.d) + self.StInit * self.d**self.j * self.u * (1-self.u**(self.i - self.j))/(1-self.u))/(self.i+self.layers_prev+1)
            self.avgMin = Amin

    # calculate representative averages
    # from large to small
    def calc_Avg_equal(self):
        for k in range(self.M+1):
            avg = (self.M-k)/self.M * self.avgMax + k/self.M * self.avgMin
            self.avgLst.append(avg)

    def calc_Avg_log(self):
        for k in range(self.M+1):
            avg = exp((self.M-k)/self.M * log(self.avgMax) + k/self.M * log(self.avgMin))
            self.avgLst.append(avg)
    
    def calc_terminalPayoff(self):
        for k in range(self.M+1):
            self.callValue.append(max(self.avgLst[k] - self.K, 0))

def average_CRR(StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed):
    dt = time_left_to_maturity/layers
    u = exp(sigma * sqrt(dt))
    d = exp(-sigma * sqrt(dt))
    p = (exp((r-q)*dt) - d)/(u - d)

    stockPrice = []
    for i in range(2, layers+2):
        stockPrice.append([0]*i)
    for i in range(layers):
        for j in range(i+2):
            stockPrice[i][j] = StInit * u**(i+1-j) * d**(j)

    TreeNodes = []
    for i in range(2, layers+2):
        TreeNodes.append([0]*i)
    for i in range(layers):
        for j in range(i+2):
            TreeNodes[i][j] = Tree_Node(time_elapsed, layers_prev, M, u, d, StInit, StAve, stockPrice[i][j], i, j, K)
            TreeNodes[i][j].calc_Amax()
            if j == 0 or j == i+1:
                pass
            else:
                TreeNodes[i][j].calc_Amin()
            if j == 0 or j == i+1:
                TreeNodes[i][j].avgLst.append(TreeNodes[i][j].avgMax)
            else:
                if log_arrayed == False:
                    TreeNodes[i][j].calc_Avg_equal()
                else:
                    TreeNodes[i][j].calc_Avg_log()

    # decide the payoffs of terminal nodes
    for j in range(layers+1):
        if j == 0 or j == layers:
            TreeNodes[layers-1][j].callValue.append(max(TreeNodes[layers-1][j].avgLst[0] - K, 0))
        else:
            TreeNodes[layers-1][j].calc_terminalPayoff()

    # backward induction
    counter = layers
    times = 0
    while times < layers-1:
        for j in range(counter):
            for avg in TreeNodes[counter-2][j].avgLst:
                if time_elapsed == 0:
                    Au = ((counter-1)*avg + StInit * u**(counter-1-j) * d**(j))/counter
                    Ad = ((counter-1)*avg + StInit * u**((counter-1)-(j+1)) * d**(j+1))/counter
                else:
                    Au = ((layers_prev+counter-1)*avg + StInit * u**(counter-1-j) * d**(j))/(layers_prev+counter)
                    Ad = ((layers_prev+counter-1)*avg + StInit * u**((counter-1)-(j+1)) * d**(j+1))/(layers_prev+counter)
                
                # sequential search
                # search for Au
                Cu, Cd = 0, 0
                for m in range(len(TreeNodes[counter-1][j].avgLst)):
                    if abs(TreeNodes[counter-1][j].avgLst[m] - Au) < 10**-8:
                        Cu = TreeNodes[counter-1][j].callValue[m]
                        break

                    if TreeNodes[counter-1][j].avgLst[m] < Au:
                        w = (TreeNodes[counter-1][j].avgLst[m-1] - Au)/(TreeNodes[counter-1][j].avgLst[m-1] - TreeNodes[counter-1][j].avgLst[m])
                        Cu = w*TreeNodes[counter-1][j].callValue[m] + (1-w)*TreeNodes[counter-1][j].callValue[m-1]
                        break

                # search for Ad
                for m in range(len(TreeNodes[counter-1][j+1].avgLst)):
                    if abs(TreeNodes[counter-1][j+1].avgLst[m] - Ad) < 10**-8:
                        Cd = TreeNodes[counter-1][j+1].callValue[m]
                        break

                    elif TreeNodes[counter-1][j+1].avgLst[m] < Ad:
                        w = (TreeNodes[counter-1][j+1].avgLst[m-1] - Ad)/(TreeNodes[counter-1][j+1].avgLst[m-1] - TreeNodes[counter-1][j+1].avgLst[m])
                        Cd = w*TreeNodes[counter-1][j+1].callValue[m] + (1-w)*TreeNodes[counter-1][j+1].callValue[m-1]
                        break
                
                discounted = (p*Cu + (1-p)*Cd) * exp(-r*dt)
                if type == 'American':
                    xValue = avg - K
                    discounted = max(xValue, discounted)
                TreeNodes[counter-2][j].callValue.append(discounted)

        counter -= 1
        times += 1
    
    # Node(0, 0)
    TreeNode_0 = Tree_Node(time_elapsed, layers_prev, M, u, d, StInit, StAve, StInit, -1, 0, K)
    TreeNode_0.avgLst.append(StAve)

    Cu = TreeNodes[0][0].callValue[0]
    Cd = TreeNodes[0][1].callValue[0]
    discounted = (p*Cu + (1-p)*Cd) * exp(-r*dt)
    if type == 'American':
        xValue = StAve - K
        discounted = max(xValue, discounted)
    TreeNode_0.callValue.append(discounted)

    print('============================================================')
    if time_elapsed == 0:
        print(f'[ Save,t = {StAve} | time elapsed = {time_elapsed} ]')
    else:
        print(f'[ Save,t = {StAve} | time elapsed = {time_elapsed} | previous layers = {layers_prev} ]')
    print(f'log arrayed = {log_arrayed}')
    print('------------------------------------------------------------')
    print(f'(CRR Binomial Tree) Price of {type} Average Call : {round(TreeNode_0.callValue[0], 4)}')
    print()

    return TreeNode_0.callValue[0]




# main
StInit = 50
StAve = 50
K = 50
r = 0.1
q = 0.05
sigma = 0.8
time_left_to_maturity = 0.25
sims = 10000
rep = 20
M = 100
layers_prev = 100
layers = 100

time_elapsed = 0
type = 'European'
log_arrayed = False
average_CRR(StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed)

# start = time.perf_counter()
# if __name__ == '__main__':
#     log_arrayed = False

#     type = 'European'
#     time_elapsed = 0
#     p1 = multiprocessing.Process(target = average_CRR, 
#                                  args = [StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed])
#     time_elapsed = 0.25
#     p2 = multiprocessing.Process(target = average_CRR, 
#                                  args = [StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed])
    
#     log_arrayed = True
#     time_elapsed = 0
#     p3 = multiprocessing.Process(target = average_CRR, 
#                                  args = [StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed])
#     time_elapsed = 0.25
#     p4 = multiprocessing.Process(target = average_CRR, 
#                                  args = [StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed])


#     type = 'American'
#     time_elapsed = 0
#     p5 = multiprocessing.Process(target = average_CRR, 
#                                  args = [StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed])
#     time_elapsed = 0.25
#     p6 = multiprocessing.Process(target = average_CRR, 
#                                  args = [StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed])
    
#     log_arrayed = True
#     time_elapsed = 0
#     p7 = multiprocessing.Process(target = average_CRR, 
#                                  args = [StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed])
#     time_elapsed = 0.25
#     p8 = multiprocessing.Process(target = average_CRR, 
#                                  args = [StAve, StInit, K, time_elapsed, time_left_to_maturity, r, q, sigma, M, layers_prev, layers, type, log_arrayed])

#     processes = [p1, p2, p3, p4, p5, p6, p7, p8]
#     for process in processes:
#         process.start()
#     for process in processes:
#         process.join()

#     finish = time.perf_counter()
#     print("============================================================")
#     print(f'Process finished in {round(finish - start, 2)} second(s).')