import sys
import subprocess
import functools

from os import path


target_path, output_file = sys.argv[1:3]

# >> grep for class definitions
grep_out = subprocess.check_output(["grep", "-rE", "^\\s*class", target_path])
raw_data = [x.split(':') for x in grep_out.decode('utf-8').split('\n') if not x.endswith(';')]

# >> parse into metainfo list [("filename", "class name", "inherits")]


def process_item(x):
    if len(x) == 3:
        f, c, i = x # file, class, inherits
    else:
        f, c = x
        i = ""
    f_name = path.basename(f)
    c_name = c.split()[-1]
    i_list = [x.strip(',{') for x in i.split() if x not in {"public", "private"}]
    return (f_name, c_name, i_list)


metainfo = list(map(process_item, [x for x in raw_data if len(x) == 3 or len(x) == 2]))

# >> clean metainfo list

# class name should contain at least one alpha char
metainfo_cleaned = [x for x in metainfo if any(i.isalpha() for i in x[1])]


# >> Convert QObject and QEvent into labels

# basic class and all its subclasses

def extract_class_list(metainfo, base_class):
    x = set([base_class])
    len_x = len(x)
    while True:
        for f, c, ix in metainfo:
            if any((i in x) for i in ix):
                x.add(c)
        if len(x) == len_x:
            break
        else:
            len_x = len(x)
    return x

# remove QObject & QEvent from class list and inherits list


def remove_basic_class(base_class, metainfo):
    r = []
    for f, c, ix in metainfo:
        if c == base_class:
            continue
        ix2 = [i for i in ix if i != base_class]
        r.append((f, c, ix2))
    return r


# do the conversion

attr_map = dict()

# QObject
qobj_class_list = extract_class_list(metainfo_cleaned, "QObject")
metainfo_q = remove_basic_class("QObject", metainfo_cleaned)

for c in qobj_class_list:
    attr_list = attr_map.get(c)
    if not attr_list:
        attr_list = set()
        attr_map[c] = attr_list
    attr_list.add("Q")


# QEvent
qevt_class_list = extract_class_list(metainfo_q, "QEvent")
metainfo_q_e = remove_basic_class("QEvent", metainfo_q)

for c in qevt_class_list:
    attr_list = attr_map.get(c)
    if not attr_list:
        attr_list = set()
        attr_map[c] = attr_list
    attr_list.add("E")


# >> generate dots graph


def add_labels(out_stream, attr_map):
    for c, attrs in attr_map.items():
        out_stream.write('"{}" [label="\\N ({})"];\n'.format(
            c,
            " ".join(sorted(attrs))))


def to_graph(out_stream, item):
    i_file, i_class, i_inherits = item
    for inherit in i_inherits:
        if inherit and i_class and any(map(lambda x: x.isalpha(), inherit)):
            out_stream.write('"{}" -> "{}";'.format(inherit, i_class))


with open("/tmp/xxx.dot", "w") as w:
    w.write("digraph qt_gui {\n")
    add_labels(w, attr_map)
    list(map(functools.partial(to_graph, w), metainfo_q_e))
    w.write("}\n")


# unflatten
subprocess.call("unflatten -l 3 -f -c 10 /tmp/xxx.dot -o /tmp/xxx_unflattened.dot".split())
# generate png
with open("/tmp/xxx.png", "w") as w:
    w.write(
        subprocess.check_output(
            "dot -Tpng /tmp/xxx_unflattened.dot".split()
        )
    )
subprocess.call(("cp /tmp/xxx.png").split() + [output_file])
