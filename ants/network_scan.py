import re
from subprocess import Popen, PIPE

class Cell:
    def __init__(self, e, l):
        self.essid = e
        self.level = l
    def __str__(self):
        return self.essid + ", " + self.level

def get_level(s):
    m = re.search("Signal level=([0-9]{1,3})/100", s)
    if m:
        return m.group(1)
    return None

def get_essid(s):
    m = re.search("ESSID:\"(.*)\"", s)
    if m:
        return m.group(1)
    return None

def get_cells(s):
    cells = []
    arr = s.split("Cell")
    index = 0
    for a in arr:
        if index != 0:
            c = Cell(get_essid(a), get_level(a))
            cells.append(c)
        index = index + 1
    return cells

def max_cell_level(arr):
    mx = 0
    index = 0
    i = 0
    for a in arr:
        if int(a.level) > mx:
            mx = int(a.level)
            index = i
        i = i + 1
    return arr[index]


def network_scan(device_name):
    p = Popen(['iwlist', device_name, 'scan'], stdout=PIPE, stderr=PIPE)
    data, error = p.communicate()
    data = str(data)
    cells = get_cells(data)
    c = max_cell_level(cells)
    print("THE CELL WITH MAXIMUM SIGNAL LEVEL is:")
    print(c.essid)
    return c.essid