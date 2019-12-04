from scipy.stats import binom

def systematic_redundancy(k, p, qos=0.9):
    # print(k, p, qos)
    assert type(k) == int
    assert type(p) == float and 0 < p <= 1
    n = k
    while dec_prob_systematic_packet(k, n, p) <= qos:
        n += 1
    return n


def dec_prob_systematic_packet(k, n, p):
    return p + ((1 - p) * binom.sf(k, n - 1, p, loc=1))


qos = 0.95
p = 0.71
k = 10
n = systematic_redundancy(k, p, qos=qos)
print(1 - dec_prob_systematic_packet(k, n, p))
print("For p: {} symbols: {} qos: {} following redundancy is needed: {} redundancy factor: {}".format(p, k, qos, int(n - k), n/k))
