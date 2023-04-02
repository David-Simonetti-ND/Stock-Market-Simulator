import matplotlib.pyplot as plt
import numpy as np

def s1(x, a, b, c):
    return a * np.sin(b * x/np.pi) + c



if __name__ == '__main__':

    init = 100
    x = []
    y = []
    for i in range(1000):
        
        x.append(i)
        tmpy = s1(i, np.abs(np.random.normal(0, .1 * init)), 1, init)
        y.append(tmpy)
    
    

    print(y)
    fig, ax = plt.subplots(1,1)
    ax.plot(x, y)
    fig.savefig('data/temp.png')
