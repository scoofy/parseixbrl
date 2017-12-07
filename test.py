import zipfile as zf
import sys, bs4, time, re
from xbrl import XBRLParser, GAAP, GAAPSerializer

def print_attributes(obj):
    for attribute in dir(obj):
        if not attribute.startswith("_"):
            print(attribute)
            print(type(attribute))
            print(getattr(obj, attribute))
            # if type(attribute) is "class":
            #     print_attributes(attribute)

def parse_it_all(filename):
    xbrl_parser = XBRLParser()
    xbrl = xbrl_parser.parse(open(filename))
    date = filename.split("-")[-1].split(".")[0]
    print(date)
    gaap_obj = xbrl_parser.parseGAAP(xbrl, doc_date=date, context="current", ignore_errors=0)
    print(gaap_obj.data)

# parse_it_all("ge10/ge-20161231.xml")

def zip_contents(zipfile):
    return zf.ZipFile(zipfile, 'r')

def simple_parse_xbrl(zipfile):
    print(zipfile)
    archive = zip_contents(zipfile)
    name_list = archive.namelist()
    print(name_list)
    main_file_name = None
    for name in name_list:
        if name.endswith(".xml") and name[-8] != "_":
            print(name)
            main_file_name = name
    xml = archive.read(main_file_name)
    soup = bs4.BeautifulSoup(xml, "lxml")
    for num in range(10):
        ixbrl_context = soup.find(id="ID_{}".format(num))
        print(ixbrl_context)
        print(ixbrl_context.text)

files = ["ge10.zip",
         "ge28.zip",
         "ge53.zip",
         "ge73.zip",
        ]


start = time.time()
print(start)


instance = simple_parse_xbrl(files[0])

stop = time.time()
print(stop)
print(stop - start)















