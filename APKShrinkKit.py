import os
import re


class ask:

    def __init__(self):
        self.res_dict = self.parse_public_xml()
        self.class_set = []
        self.id_set = []
        self.layout_files = []
        self.smali_files = []
        self.lib_classes = []
        self.res_regex = re.compile(r'(?<=@)[0-9A-Za-z-_]+\/[0-9A-Za-z-_]+')
        self.class_regex = re.compile(r'(?<=")([A-Za-z][0-9A-Za-z-_$]+(\.[A-Za-z][0-9A-Za-z-_$]+)+)(?=")')
        self.lib_regex = re.compile(r'([A-Za-z][0-9A-Za-z-_$]+(\/[A-Za-z][0-9A-Za-z-_$]+)+)(?=\\x00)')
        self.smali_regex = re.compile(r'(?<=L)[0-9A-Za-z-_$\/]+?(?=;)')
        self.id_regex = re.compile(r'0x7f'+self.get_id_regex_range()+r'[0-9a-f]{4}(?=\s)')
        self.construct()

    def construct(self):
        lib_strs = self.get_lib_strs()
        for layout_dir in [x for x in os.listdir('res') if 'layout' in x]:
            for root, dirs, files in os.walk(layout_dir):
                for file in files:
                    self.layout_files.append(root+'/'+file)
        for smali_dir in [x for x in os.listdir('.') if 'smali' in x]:
            for root, dirs, files in os.walk(smali_dir):
                for file in files:
                    path = root+'/'+file
                    self.smali_files.append(path)
                    strcl = path.split('/', 1)[1].split('.')[0]
                    strcls = strcl.split('/', 1)
                    # Assuming all libs are used
                    for lib_str in lib_strs:
                        libs = lib_str.split('/', 1)
                        if libs[0].endswith(strcls[0]) and strcls[1] == libs[1]:
                            self.lib_classes.append(strcl)
                            break

    def analyze(self):
        self.arsc_search()
        self.xml_search('AndroidManifest.xml')
        for lib_class in self.lib_classes:
            self.class_search(lib_class)
        return self

    def write_to_file(self):
        with open('unused_ids.txt', 'w') as f:
            for id in self.get_unused_ids():
                f.write(id+'\n')
        with open('unused_classes.txt', 'w') as f:
            for clazz in self.get_unused_classes():
                f.write(clazz+'\n')
        with open('unused_res.txt', 'w') as f:
            for res in self.get_unused_res():
                f.write(res+'\n')

    def read_from_file(self):
        with open('unused_ids.txt', 'r') as f:
            self.id_set = [x.strip() for x in f.readlines()]
        with open('unused_classes.txt', 'r') as f:
            self.class_set = [x.strip() for x in f.readlines()]
        with open('unused_res.txt', 'r') as f:
            self.res_set = [x.strip() for x in f.readlines()]

    def get_lib_strs(self):
        strs = []
        if os.path.exists('lib'):
            arch = os.listdir('lib')[0]
            for file in os.listdir('lib/'+arch):
                with open('lib/'+arch+'/'+file, 'rb') as f:
                    strs += self.lib_regex.findall(str(f.read()))
        return [x[0] for x in strs]

    def parse_public_xml(self):
        res = []
        with open('res/values/public.xml') as f:
            lines = f.readlines()
        for line in lines:
            if '<public' in line:
                a = line.replace('"', '').replace('=', ' ').split()
                res.append({a[1]: a[2], a[3]: a[4], a[5]: a[6]})
        return res

    def id2name(self, id):
        for item in self.res_dict:
            if item['id'] == id:
                return item['type'], item['name']
        return('', '')

    def name2id(self, type, name):
        for item in self.res_dict:
            if item['type'] == type and item['name'] == name:
                return item['id']

    def get_id_regex_range(self):
        a = [x['id'][4:6] for x in self.res_dict][-1]
        m = int(a, 16)
        if m > 0x10:
            return r'[0-'+a[0]+r'][0-9a-f]'
        if m > 0x09:
            return r'0[1-9a-'+a[1]+r']'
        return r'0[1-'+a[1]+r']'

    def class_search(self, clazz):
        self.class_set.append(clazz)
        for smali_file in self.smali_files:
            if clazz in smali_file:
                with open(smali_file, 'r') as f:
                    used_classes2 = self.smali_regex.findall(f.read())
                with open(smali_file, 'r') as f:
                    ids = self.id_regex.findall(f.read())
                for clazz2 in used_classes2:
                    if clazz2 not in self.class_set:
                        self.class_search(clazz2)
                for id in ids:
                    if id not in self.id_set:
                        self.id_search(id)

    def id_search(self, id):
        self.id_set.append(id)
        type, name = self.id2name(id)
        results = []
        for type_dir in [x for x in os.listdir('res') if type in x]:
            for root, dirs, files in os.walk('res/'+type_dir):
                for file in files:
                    if file == name+'.xml':
                        results.append(root+'/'+file)
        for result in results:
            self.xml_search(result)

    def xml_search(self, path):
        with open(path, 'r') as f:
            names = self.res_regex.findall(f.read())
        with open(path, 'r') as f:
            classes = self.class_regex.findall(f.read())
        for name in names:
            id = self.name2id(name.split('/')[0], name.split('/')[1])
            if id not in self.id_set:
                self.id_search(id)
        if classes:
            for clazz in [x[0].replace('.', '/') for x in classes]:
                if clazz not in self.class_set:
                    self.class_search(clazz)

    def arsc_search(self):
        arsc_dirs = [x for x in os.listdir('res') if 'values' in x]
        for arsc_dir in arsc_dirs:
            for root, dirs, files in os.walk('res/'+arsc_dir):
                for file in files:
                    if file != 'public.xml':
                        with open(root+'/'+file, 'r') as f:
                            names = self.res_regex.findall(f.read())
                        for name in names:
                            id = self.name2id(name.split(
                                '/')[0], name.split('/')[1])
                            if id not in self.id_set:
                                self.id_search(id)

    def get_unused_ids(self):
        return [x['id'] for x in self.res_dict if x['id'] not in self.id_set]

    def get_unused_classes(self):
        return [x for x in self.smali_files if x.split('/', 1)[1].split('.')[0] not in self.class_set]

    def get_unused_res(self):
        res = []
        for id in self.get_unused_ids():
            type, name = self.id2name(id)
            for type_dir in [x for x in os.listdir('res') if x.startswith(type)]:
                for root, dirs, files in os.walk('res/'+type_dir):
                    for file in files:
                        if file.startswith(name+'.'):
                            res.append(root+'/'+file)
        return res
