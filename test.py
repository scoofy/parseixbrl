import zipfile as zf
import sys, bs4, time, re

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
    ixbrl_context = soup.find("xbrli:context")
    attribute_list = []
    if ixbrl_context:
        print(ixbrl_context)
        for item in ixbrl_context:
            if item:
                try:
                    item.text
                except:
                    pass
                for attribute in dir(item):
                    if not attribute.startswith("_"):
                        if not attribute in attribute_list:
                            attribute_list.append(attribute)

    print(attribute_list)



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















