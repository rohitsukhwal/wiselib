#!/usr/bin/env python3

import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt
from pylab import setp
import math
import re
import io
from matplotlib import rc
import sys
import time
from matplotlib import ticker
import os.path
import pickle

sys.path.append('/home/henning/bin')
from experiment_utils import quantize, fold, median, join_boxes, average, materialize

INDIVIDUAL_PLOTS = False
#INDIVIDUAL_PLOTS = True


PLOT_DIR = 'plots'

# seconds
MEASUREMENT_INTERVAL = 64.0 / 3000.0

# mA
CURRENT_FACTOR = 70.0 / 4095.0

# mA * 3300mV = microJoule (uJ)
CURRENT_DISPLAY_FACTOR = 3300.0

EXPERIMENT_INTERVAL = 600.0
BOX_INTERVAL = 5.0



rc('font',**{'family':'serif','serif':['Palatino'], 'size': 12})
rc('text', usetex=True)
#fs = (12, 5)
fs = (8, 3)


#
# Blacklist
#

energy_measurements_broken = set([
    #10004, 10037, 10044
])

# Nodes that did not connect (permanently) in 3600s
always_active = set([
    #10008, 10009, 10013, 10050
])

# Nodes that consume energy as if the radio was permanently on when
# a MAC layer should have been active
high_energy = set([
    #10042
])

root = set([
    #10029
])

blacklist = {
        '25458.csv': { 10009, 10037, 10044, 10029 },
        '25464.csv': { 10009, 10037, 10044, 10005, 10010 },
        '25465.csv': { 10009, 10037, 10044, 10005, 10017 },
        '25466.csv': { 10009, 10037, 10044, 10200 },
        '25469.csv': { 10009, 10037, 10044, 10035, 10056, 10037, 104117, 10199, 10200 },
        '25470.csv': { 10009, 10037, 10044, 10033, 10030 },
        '25473.csv': { 10009, 10037, 10044, 10039 },
        '25474.csv': { 10009, 10037, 10044, 10027, 10041 },
        '25475.csv': { 10009, 10037, 10044, 10031, 10027, 10037, 10044 },
        #'25476.csv':  10009, 10037, 10044,  },
        '25477.csv': { 10009, 10037, 10044, 10007,10010,10023,10046,10047 },
        '25478.csv': { 10009, 10037, 10044, 10042,10018,10008,10025 },
        '25479.csv': { 10009, 10037, 10044, 10035 },
        #'25480.csv':  10009, 10037, 10044,  },
        '25487.csv': { 10009, 10037, 10044, 10037, 10031, 10009, 10038 },
        '25488.csv': { 10009, 10037, 10044, 10009, 10199 },
        #'25489.csv':  10009, 10037, 10044,  },
        '25493.csv': { 10009, 10037, 10044, 10037, 10044 },
        '25516.csv': { 10009, 10037, 10044, 10027, 10050, 10042, 10037, 10044 },
        '25515.csv': { 10009, 10037, 10044, 10010 },
        '25577.csv': { 10009, 10037, 10044, 10014, 10007, 10004, 10037, 10044 },
        '26034.csv': { 10009, 10037, 10044, 10200 },
        '26045.csv': { 10009, 10037, 10044, 10200 },
        '26064.csv': { 10009, 10037, 10044, 10007, 10011, 10027, 10029, 10039 },
        '26073.csv': { 10009, 10037, 10044, 10012, 10027, 10029, 10033, 10053 },
        '26080.csv': { 10009, 10037, 10044, 10010, 10054, 10038 },
        '26082.csv': { 10009, 10037, 10044, 10041, 10053, 10041 },

        '26205.csv': { 10009, 10037, 10044, 10005, 10018, 10042 },
        '26207.csv': { 10020, 10037, 10044, 10053, 10054 },
        '26210.csv': { 10035, 10037, 10039, 10044, 10053, 10054 },

        '26245.csv': { 10014, 10025, 10037, 10044, 10052, 10031, 10027, 10200 },
        '26246.csv': { 10019, 10044, 10047 },
        '26247.csv': { 10008, 10018, 10037, 10039, 10044, 10045 },
        '26249.csv': { 10018, 10030, 10025, 10037, 10039, 10044, 10045, },

        # Temperature
        '26250.csv': { 10001, 10018, 10030, 10012, 10020, 10021, 10027, 10037, 10038, 10039, 10041,
            10043, 10044, 10050, 10054, },
        '26251.csv': { 10037, 10044, 10053 },
        '26252.csv': { 10008, 10021, 10023, 10027, 10029, 10037, 10041, 10045, 10053, 10054 },

        # Room Light 10
        '26253.csv': { 10001, 10005, 10008, 10010, 10011, 10014, 10019, 10025, 10037,
            10042, 10044, 10045, 10053, },
}





class Timer:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        print('{}...'.format(self.name))
        self.t = time.time()

    def __exit__(self, *args):
        print(' {} done ({}s)'.format(self.name, time.time() - self.t))


def parse(fn):
    print("=== {}".format(fn))
    pickled_fn = fn + '.p'
    if os.path.exists(pickled_fn):
        with Timer("unpickling {}".format(pickled_fn)):
            d = pickle.load(open(pickled_fn, 'rb'))

    else:
        with Timer("reading {}".format(fn)):
            data = np.genfromtxt(fn, delimiter = '\t', skip_header=0, names=True, usecols=('avg','motelabMoteID'),
                    dtype=[('avg', 'i4'), ('motelabMoteID', 'i4')])

        with Timer('refudelling'):
            # split into columns
            d = defaultdict(list)
            for avg, mote_id in data:
                #if mote_id not in blacklist:
                d[mote_id].append(avg)

        print("  considered {} motes".format(len(d)))

        with Timer('converting'):
            for k in d.keys():
                d[k] = np.array(d[k])
                #print(k, d[k])

        with Timer("pickling {}".format(pickled_fn)):
            pickle.dump(d, open(pickled_fn, 'wb'))

    for mote_id in blacklist.get(fn, set()):
        if mote_id in d:
            del d[mote_id]

    return d

def moving_average(a, n=3) :
    """
    sauce: http://stackoverflow.com/questions/14313510/moving-average-function-on-numpy-scipy
    """
    ret = np.cumsum(a, dtype=float)
    ret[n:] = (ret[n:] - ret[:-n]) / n
    #print(len(a), len(ret), n)
    ret[:n] = ret[:n] / (np.arange(n) + 1)
    return ret

def plot(ax, vs, name, style):
    print("plotting {}...".format(name))
    #ax.set_xlim((50000 * MEASUREMENT_INTERVAL, 100000 * MEASUREMENT_INTERVAL))
    #ax.set_xlim((2000, 2100))
    #ax.set_ylim((0, 2))
    #for k, vs in d.items():
    ts = np.arange(len(vs)) * MEASUREMENT_INTERVAL
    vs = vs * CURRENT_FACTOR
    #ax.plot(ts, vs, color='#aadddd')

    vs = moving_average(vs, int(60.0 / MEASUREMENT_INTERVAL)) # avg over 10s
    ax.plot(ts, vs, label=name, **style)

    #ax.plot([0, ts[-1]], [IDLE_CONSUMPTION, IDLE_CONSUMPTION], color='#ff9999', linewidth=3)


#d = parse('25446.csv')
#d = parse('25458.csv.tmp')


def plotone(vs, name, style):
    #print("  plotting {}...".format(name))
    fig = plt.figure(figsize=fs)
    ax = fig.add_subplot(111)
    #ax.set_ylim((0, 10))
    ax.set_ylabel('$I$ / mA')
    ax.set_xlabel('$t$ / s')
    ax.set_ylim((0, 3))
    #ax.set_xlim((50000 * MEASUREMENT_INTERVAL, 100000 * MEASUREMENT_INTERVAL))
    #ax.set_xlim((4000, 5000))
    #ax.set_xlim((760, 850))
    #ax.set_ylim((0, 2))
    #for k, vs in d.items():
    ts = np.arange(len(vs)) * MEASUREMENT_INTERVAL
    vs = vs * CURRENT_FACTOR
    #ax.plot(ts, vs, color='#aadddd')

    vs = moving_average(vs, int(5.0 / MEASUREMENT_INTERVAL)) # avg over 10s
    #ax.set_xlim((500, 510))
    ax.plot(ts, vs, **style)
    ax.grid()
    #fig.savefig(PLOT_DIR + '/energy_{}.pdf'.format(name), bbox_inches='tight', pad_inches=.1)
    fig.savefig(PLOT_DIR + '/energy_{}.png'.format(name), bbox_inches='tight', pad_inches=.1)
    plt.close(fig)


def compute_boxplot(vs, experiment_interval=EXPERIMENT_INTERVAL):
    #box_entries = int(10.0 / MEASUREMENT_INTERVAL)
    box_entries = int(BOX_INTERVAL / MEASUREMENT_INTERVAL)

    ts = np.arange(len(vs)) * MEASUREMENT_INTERVAL
    #return fold(quantize(zip(ts, vs), box_entries), int(experiment_interval / (box_entries * MEASUREMENT_INTERVAL)), skip = 1)
    return fold(quantize(zip(ts, vs), box_entries), int(EXPERIMENT_INTERVAL / (box_entries * MEASUREMENT_INTERVAL)), skip = 1)

def style_box(bp, s):
    for key in ('boxes', 'whiskers', 'fliers', 'caps', 'medians'):
        plt.setp(bp[key], **s)
    plt.setp(bp['fliers'], marker='+')

def data_to_boxes(d, label, style, experiment_interval=EXPERIMENT_INTERVAL):
    #l = min((len(x) for x in d.values() if len(x)))
    #l = None
    #for k, v in d.values():

    print("=== {}".format(label))

    l, k = max(((len(v), k) for k, v in d.items() if len(v)))
    print("  max l={} k={}".format(l, k))
    l, k = min(((len(v), k) for k, v in d.items() if len(v)))
    print("  min l={} k={}".format(l, k))

    #print("l({})={}".format(label, l))
    with Timer("summing up"):
        sums = np.zeros(l)
        for k,v in d.items():
            if INDIVIDUAL_PLOTS:
                plotone(v, label + '_' + str(k), style)
            sums += v[:l]
    with Timer("computing box plot"):
        #r = compute_boxplot(CURRENT_FACTOR * sums / len(d), experiment_interval)
        r = compute_boxplot(CURRENT_FACTOR * sums / len(d), EXPERIMENT_INTERVAL)
    r = materialize(r)
    return r

def plot_boxes(ax, it, label, style, **kws):
    #print(list(it))
    vs2 = [v for (t, v) in it]
    print("-- {} {}".format(label, ' '.join(str(len(x)) for x in vs2)))
    bp = ax.boxplot(vs2, positions=[x+.5 for x in range(len(vs2))])
    style_box(bp, style)
    #ax.plot(range(1, len(vs2) + 1), [average(x) for x in vs2], label=label, **style)
    ax.plot([0], [0], label=label, **style)

#data = [
        ##('Test', parse('26034.csv'), {'color': '#bbaa88'}), #{'color': '#88bbbb'}),
        ##('Simple Temperature', parse('26034.csv'), {'color': '#dd7777'}), #{'color': '#88bbbb'}),
        #('Simple Temperature II', parse('26052.csv'), {'color': '#dd7777'}), #{'color': '#88bbbb'}),
        #('Simple Temperature III', parse('26064.csv'), {'color': 'black'}), #{'color': '#88bbbb'}),
        ##('Idle', parse('26053.csv'), {'color': '#88bbbb'}), #{'color': '#88bbbb'}),
        ##('Collect-All', parse('26045.csv'), {'color': '#bbaa88'}),
#]

fig = plt.figure(figsize=fs)
ax = fig.add_subplot(111)
ax.set_ylabel('$I$ / mA')
ax.set_xlabel('$t$ / s')
#ax.set_ylim((0.7, 2.0))
#ax.set_yscale('log')
#ax.set_ylim((0.7, 2.0))
#ax.set_xlim((0,300))

# 
# Experiments for simple temperature query
#
#kws = { 'style': { 'color': 'black', 'linestyle': '-'}, 'label': 'Temperature Old' }
#boxes = materialize(data_to_boxes(parse(x + '.csv'), **kws) for x in ('26052', '26064'))
##it = join_boxes(boxes)
#j = list(join_boxes(*boxes))
#plot_boxes(ax, j, **kws)

#kws = { 'style': { 'color': '#88bbbb', 'linestyle': '-'}, 'label': 'Idle' }
#plot_boxes(ax, data_to_boxes(parse('26053.csv'), **kws), **kws)

kws = { 'style': { 'color': 'black', 'linestyle': '-'}, 'experiment_interval': 600.0, 'label': 'Idle' }
plot_boxes(
    ax,
    data_to_boxes(parse('26252.csv'), **kws),
    #join_boxes(
        #data_to_boxes(parse('26205.csv'), **kws),
        #data_to_boxes(parse('26245.csv'), **kws),
    **kws)

#kws = { 'style': { 'color': '#dd7777', 'linestyle': ':'}, 'label': 'Collect Old' }
#plot_boxes(ax, data_to_boxes(parse('26045.csv'), **kws), **kws)

#kws = { 'style': { 'color': 'grey', 'linestyle': '-'}, 'label': 'Temperature' }
#plot_boxes(ax, data_to_boxes(parse('26073.csv'), **kws), **kws)

# Broken! Lost lots of messages due to send storming,
# after this implemented rate-limited queries
#kws = { 'style': { 'color': '#dd7777', 'linestyle': '-'}, 'label': 'Collect' }
#plot_boxes(ax, data_to_boxes(parse('26074.csv'), **kws), **kws)

# This is the debug run of the code of 26080 (...79):
#generic_apps/inqp_test evaluation/snes M?% grep ACKED 26079/*/output.txt |wc -l
#4263
#generic_apps/inqp_test evaluation/snes M?% grep ABRT 26079/*/output.txt |wc -l
#368
#generic_apps/inqp_test evaluation/snes M?% grep QUEUE 26079/*/output.txt |wc -l
#57
#kws = { 'style': { 'color': '#bbaa88', 'linestyle': ':'}, 'label': 'Collect' }
#plot_boxes(ax, data_to_boxes(parse('26080.csv'), **kws), **kws)

kws = { 'style': { 'color': '#bbaa88', 'linestyle': '-'}, 'label': 'Collect' }
plot_boxes(
    ax,
    #data_to_boxes(parse('26210.csv'), **kws),
    #data_to_boxes(parse('26247.csv'), **kws),
    #data_to_boxes(parse('26248.csv'), **kws),
    data_to_boxes(parse('26249.csv'), **kws),
    **kws)


# Debug run for 26082 (...81):
#
#generic_apps/inqp_test evaluation/snes M?% grep ACKED 26081/*/output.txt |wc -l
#445
#generic_apps/inqp_test evaluation/snes M?% grep ABRT 26081/*/output.txt |wc -l 
#58
#generic_apps/inqp_test evaluation/snes M?% grep QUEUE 26081/*/output.txt |wc -l
#1
kws = { 'style': { 'color': '#88bbbb', 'linestyle': '-'}, 'experiment_interval': 600.0, 'label': 'Temperature' }
plot_boxes(ax,
        #data_to_boxes(parse('26082.csv'), **kws),
        data_to_boxes(parse('26250.csv'), **kws),
        **kws)


# query_roomlight10, CSMA, NULLRDC
#generic_apps/inqp_test evaluation/snes M?% grep ACKED 26175/*/output.txt|wc -l                                 
#865
#generic_apps/inqp_test evaluation/snes M?% grep ABRT 26175/*/output.txt|wc -l                                 
#275
#generic_apps/inqp_test evaluation/snes M?% grep QUEUE 26175/*/output.txt|wc -l                                 
#0
# 


# query_roomlight10, CSMA, NULLRDC, aggrinterval = 5000
kws = { 'style': { 'color': '#dd7777', 'linestyle': '-'}, 'experiment_interval': 600.0, 'label': 'Light in Room 10' }
plot_boxes(
        ax,
        #join_boxes(
            #data_to_boxes(parse('26207.csv'), **kws),
            #data_to_boxes(parse('26246.csv'), **kws)
        #),
        data_to_boxes(parse('26253.csv'), **kws),
        **kws
)



ax.set_xticks(range(0, int(EXPERIMENT_INTERVAL / BOX_INTERVAL) + 1, int(EXPERIMENT_INTERVAL / (10 * BOX_INTERVAL))))
ax.set_xticklabels(range(0, int(EXPERIMENT_INTERVAL + BOX_INTERVAL), int(EXPERIMENT_INTERVAL / 10.0)))
ax.grid(True, which='both')
ax.legend(ncol=4, bbox_to_anchor=(1.0, 0), loc='lower right', prop={'size': 9})
#ax.legend(ncol=2, bbox_to_anchor=(1.0, 1.00), loc='upper right')
#ax.legend(loc='upper right')


fig.savefig(PLOT_DIR + '/energy_sum.png')
fig.savefig(PLOT_DIR + '/energy_sum.pdf', bbox_inches='tight', pad_inches=.1)
plt.close(fig)

# vim: set ts=4 sw=4 expandtab:

