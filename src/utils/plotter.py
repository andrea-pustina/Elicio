import numpy as np
#import matplotlib; matplotlib.use("TkAgg")
import matplotlib.pyplot as plt


def plot_histogram(values, title='Histogram'):
    if len(values) == 0:
        print('anything to plot')
        return

    n, bins, patches = plt.hist(x=values, bins='auto', color='#0504aa', alpha=0.7, rwidth=0.85, density=True)

    plt.grid(axis='y', alpha=0.75)
    plt.xlabel('Value')
    plt.ylabel('Frequency')
    plt.title(title)
    plt.text(23, 45, r'$\mu=15, b=3$')

    # Set a clean upper y-axis limit.
    maxfreq = n.max()
    plt.ylim(ymax=np.ceil(maxfreq / 10) * 10 if maxfreq % 10 else maxfreq + 10)

    plt.show()