import xarray
def combine_hmfn(h, m, f, n):
    ds = xarray.concat([h, m, f, n], dim="count").assign_coords({"count": ["hits", "misses", "false alarms", "correct nulls"]})
    return ds

def csi(contingency_table):
    s = contingency_table.sel(count="hits") / (
        contingency_table.sel(count="hits")
        + contingency_table.sel(count="misses")
        + contingency_table.sel(count="false alarms")
    )
    s.name = "critical success index"
    s.attrs["short_name"] = "csi"
    return s


def total(contingency_table):
    s = (
        contingency_table.sel(count="hits")
        + contingency_table.sel(count="misses")
        + contingency_table.sel(count="false alarms")
        + contingency_table.sel(count="correct nulls")
    )
    s.name = "total"
    s.attrs["short_name"] = "total"
    return s


def far(contingency_table):
    s = contingency_table.sel(count="false alarms") / (
        contingency_table.sel(count="false alarms")
        + contingency_table.sel(count="hits")
    )
    s.name = "false alarm ratio"
    s.attrs["short_name"] = "far"
    return s



def pofd(contingency_table):
    s = contingency_table.sel(count="false alarms") / (
        contingency_table.sel(count="false alarms")
        + contingency_table.sel(count="correct nulls")
    )
    s.name = "probability of false detection"
    s.attrs["short_name"] = "pofd"
    return s


def pod(contingency_table):
    s = contingency_table.sel(count="hits") / (
        contingency_table.sel(count="hits") + contingency_table.sel(count="misses")
    )
    s.name = "probability of detection"
    s.attrs["short_name"] = "pod"
    return s


def hk(contingency_table):
    s = (
        contingency_table.sel(count="hits") * contingency_table.sel(count="correct nulls")
        - contingency_table.sel(count="misses") * contingency_table.sel(count="false alarms")
    ) / (
        (contingency_table.sel(count="hits") + contingency_table.sel(count="misses"))
        * (
            contingency_table.sel(count="false alarms")
            + contingency_table.sel(count="correct nulls")
        )
    )
    # I couldn't derive hk = pod - pofd. Are they almost equal?
    # print(max(abs((s - pod(contingency_table) + pofd(contingency_table)))))
    s.name = "Hanssen and Kuipers discriminant"
    s.attrs["short_name"] = "hk"
    return s


def accuracy(contingency_table):
    N = total(contingency_table)
    s = (contingency_table.sel(count="hits") + contingency_table.sel(count="correct nulls")) / N
    s.name = "accuracy"
    s.attrs["short_name"] = "acc"
    return s

def bias(contingency_table):
    F = contingency_table.sel(count="hits") + contingency_table.sel(count="false alarms")
    O = contingency_table.sel(count="hits") + contingency_table.sel(count="misses")
    s = F/O
    s.name = "multiplicative bias"
    s.attrs["short_name"] = "mbias"
    return s


def hss(contingency_table):
    """
    Wilks 2nd ed. Eqn 7.15
    Written differently but equivalently in
    https://www.cawcr.gov.au/projects/verification/#Methods_for_dichotomous_forecasts
    Disagreement over lowest possible value. cawcr says -1; other sites say -inf. I think it is -1.
    """

    a = contingency_table.sel(count="hits")
    b = contingency_table.sel(count="false alarms")
    c = contingency_table.sel(count="misses")
    d = contingency_table.sel(count="correct nulls")
    
    numerator = 2 * (a*d-b*c)

    denom = (a+c)*(c+d) + (a+b)*(b+d)
    
    hss = numerator / denom
    hss.name = "Heidke Skill Score"
    hss.attrs["short_name"] = "hss"
    return hss

def ets(contingency_table):
    O = contingency_table.sel(count="hits") + contingency_table.sel(count="misses")
    F = contingency_table.sel(count="hits") + contingency_table.sel(count="false alarms")
    N = total(contingency_table)
    r = O * F / N
    s = (contingency_table.sel(count="hits") - r) / (
        O + F - contingency_table.sel(count="hits") - r
    )
    # hits - r leaves a zero-dimensional coordinate "count" that equals "hits"
    # that I have to remove.
    s = s.reset_coords("count", drop=True) 
    s.name = "equitable threat score"
    s.attrs["short_name"] = "ets"
    return s
