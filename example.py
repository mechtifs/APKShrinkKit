from APKShrinkKit import ask
import os
import sys

# If the apk file is way too complicated, try setting recursion limit to a higher value
sys.setrecursionlimit(3000)

# Use Apktool to decompile the apk file first
a = ask()

# Analyze then export the results to txt files
a.analyze().write_to_file()

# Garbage collection for smali files
for i in ask.get_unused_classes():
    os.remove(i)

# Only run this if there's no obfuscation
for i in ask.get_unused_res():
    os.remove(i)

# Else you need to extract the resources from the apk file and specify a dictionary of corresponding resource paths
# The example below is only capable for 'r/xxx/xxx' structure
res_dict = {}
for dir in os.listdir('res'):
    res_dict.update({dir: os.listdir('res/'+dir)})
r_dict = {}
for dir in os.listdir('r'):
    for key, value in res_dict.items():
        if os.listdir('r/'+dir) == value:
            r_dict.update({key: dir})
for i in ask.get_unused_res():
    ispl = i.split('/')
    path = 'r/'+r_dict[ispl[1]]+'/'+ispl[2]
    if os.path.exists(path):
        os.remove(path)
