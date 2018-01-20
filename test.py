import zipfile as zf
import sys, time, re
import xml.etree.ElementTree as ET
import pprint as pp
from bs4 import BeautifulSoup
from xbrl import XBRLParser, GAAP, GAAPSerializer
import logging
logging.basicConfig(format='  ---- %(filename)s|%(lineno)d ----\n%(message)s', level=logging.DEBUG)

def print_attributes(obj):
    for attribute in dir(obj):
        if not attribute.startswith("_"):
            logging.info(attribute)
            logging.info(type(attribute))
            logging.info(getattr(obj, attribute))
            # if type(attribute) is "class":
            #     print_attributes(attribute)

def parse_it_all(filename):
    xbrl_parser = XBRLParser()
    xbrl = xbrl_parser.parse(open(filename))
    date = filename.split("-")[-1].split(".")[0]
    logging.info(date)
    gaap_obj = xbrl_parser.parseGAAP(xbrl, doc_date=date, context="current", ignore_errors=0)
    logging.info(gaap_obj.data)

def element_walk(element, count=0):
    for child in element:
        print("\t"*count + str(child))
        if len(child):
            element_walk(child, count = count + 1)

def return_context_id(context_element):
    context_reference = context_element.get("id")
    return context_reference

# parse_it_all("ge10/ge-20161231.xml")



def zip_contents(zipfile):
    return zf.ZipFile(zipfile, 'r')

def simple_parse_xbrl(zipfile):
    ticker = None
    logging.info(zipfile)
    archive = zip_contents(zipfile)
    name_list = archive.namelist()
    main_file_name = None
    for name in name_list:
        if name.endswith(".xml") and "_" not in name:
            logging.info(name)
            ticker = name.split("-")[0].upper()
            print("ticker: " + ticker)
            main_file_name = name

    ns = {}
    for event, (name, value) in ET.iterparse(archive.open(main_file_name), ['start-ns']):
        if name:
            ns[name] = value
    # pp.pprint(ns)

    tree = ET.parse(archive.open(main_file_name))
    root = tree.getroot()
    for element in tree.findall("xbrli:context", ns):
        cik = None
        period = {}
        fact_dict = {}
        for item in element.iter():
            print(item.tag)
            if "identifier" in item.tag:
                if "scheme" in item.attrib.keys():
                    scheme = item.attrib.get("scheme")
                    if scheme == "http://www.sec.gov/CIK":
                        fact_dict["CIK"] = item.text

            elif "explicitMember" in item.tag:
                if "dimension" in item.attrib.keys():
                    segment = fact_dict.get("segment")
                    if not segment:
                        segment = {}
                        fact_dict["segment"] = segment
                    segment[item.attrib.get("dimension")] = item.text
            elif "startDate" in item.tag:
                period["startDate"] = item.text
            elif "endDate" in item.tag:
                period["endDate"] = item.text
            elif "instant" in item.tag:
                period["instant"] = item.text
            elif "forever" in item.tag:
                period["forever"] = item.text
        fact_dict["period"] = period
        context_id = return_context_id(element)
        context_ref_list = [x for x in root if x.get("contextRef") == context_id]

        for context_element in context_ref_list:
            if "TextBlock" in str(context_element.tag):
                continue
            elif "&lt;" in str(context_element.text):
                continue
            elif "<div " in str(context_element.text) and "</div>" in str(context_element.text):
                continue
            else:
                pass
            context_id_short = context_id.split("}")[-1]
            context_element_dict = context_element.attrib
            tag = context_element.tag
            short = tag.split("}")[-1]

            context_element_dict[short] = context_element.text
            # context_element_dict["period"] = period

            fact_dict[context_id_short + ":" + short] = context_element_dict
            if context_element_dict:
                break
        ticker_dict = {ticker: fact_dict}
        # print("\n"*10)
        pp.pprint(ticker_dict)
        sys.exit()
    # rando = tree[100]
    # print(rando.attrib)
    # print(rando.attrib.keys())
    # for element in rando.iter():
    #     print(element)
    #     print(element.attrib)
    #     print(element.attrib.keys())
    # for element in tree.iter():
    #     pp.pprint(element.attrib)
    #     if "unitref" in element.attrib.keys():
    #         print("\t\t" + str(element))
    #         print("\t" + str(element.text))
    #         for subelement in element.iter():
    #             print(subelement)
    sys.exit()
    the_xml = archive.read(main_file_name)
    soup = BeautifulSoup(the_xml, "lxml")
    data_list = []
    attribute_set = set([])
    contextref_set = set([])
    everything_list = soup.find_all()
    tag_list = [tag.name for tag in everything_list]
    tag_set = set(tag_list)
    #logging.info(tag_set)
    single_element_list = [element for element in everything_list if ":" in element.name and tag_list.count(element.name)==1] #or use defaultdict from the collections,if perfomance matters:
    count = 0
    for element in single_element_list:
        if len(str(element.string)) < 100:
            print(element.name)
            print(element.string)
            count+=1
        else:
            pass
            #print(element.name)
            #pp.pprint(element.string)
    print(len(single_element_list))
    print(count)

    # id_num_list = soup.find_all(id=re.compile("^ID_"))
    # fact_hash_list = soup.find_all(id=re.compile("^Fact-"))
    # all_the_shit = id_num_list + fact_hash_list
    # logging.info("len(all_the_shit): {}".format(len(all_the_shit)))
    # for xbrl_entity in all_the_shit:
    #     name = xbrl_entity.name
    #     contents = xbrl_entity.contents
    #     attr_dict = xbrl_entity.attrs
    #     attr_dict['contents'] = contents
    #     my_dict = {"name": attr_dict}
    #     data_list.append(my_dict)
    #     attribute_set.add(xbrl_entity.name)
    #     contextref_set.add(xbrl_entity.get("contextref"))
    # return attribute_set, contextref_set

files = ["aro111.zip",
         "ge10.zip",
         "ge28.zip",
         "ge53.zip",
         "ge73.zip",
        ]

start = time.time()
logging.info(start)


simple_parse_xbrl(files[0])
sys.exit()

stop = time.time()
logging.info(stop)














