from xbrl import XBRLParser, GAAP, GAAPSerializer
from xbrl_edit import XBRL
import zipfile as zf
import bs4, time, re

xbrl_parser = XBRLParser()
def parse_xbrl(zipfile):
    print(zipfile)
    archive = zf.ZipFile(zipfile, 'r')
    name_list = archive.namelist()
    # print(name_list)
    xml = archive.read(name_list[0])
    x = XBRL(zipfile, xml)
    return x.fields
    #xbrl = xbrl_parser.parse(name_list[0])
    #soup.prettify(xml)

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
    gaap = soup.find("xbrli:context")
    if gaap:
        print(gaap)
        for div in gaap:
            if div.unit_ref:
                print(div)

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















