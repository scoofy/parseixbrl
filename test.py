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
    # logging.info(zipfile)
    archive = zip_contents(zipfile)
    name_list = archive.namelist()
    main_file_name = None
    for name in name_list:
        if name.endswith(".xml") and "_" not in name:
            # logging.info(name)
            ticker = name.split("-")[0].upper()
            main_file_name = name

    ns = {}
    for event, (name, value) in ET.iterparse(archive.open(main_file_name), ['start-ns']):
        if name:
            ns[name] = value

    tree = ET.parse(archive.open(main_file_name))
    root = tree.getroot()
    for element in tree.findall("xbrli:context", ns):
        cik = None
        period = {}
        fact_dict = {}
        for item in element.iter():
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

        ticker_dict = {ticker: fact_dict}
        return(ticker_dict)

files = ["aro111.zip",
         "ge10.zip",
         "ge28.zip",
         "ge53.zip",
         "ge73.zip",
        ]


from itertools import islice

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))
number_of_items = 5
start = time.time()
logging.info(start)

for file in files:
    stock_dict = simple_parse_xbrl(file)
    ticker = list(stock_dict.keys())[0]
    data_dict = list(stock_dict.values())[0]
    some_items = dict(take(number_of_items, data_dict.items()))
    pp.pprint({ticker: some_items})


stop = time.time()
logging.info(stop)














