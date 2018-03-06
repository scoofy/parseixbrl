import zipfile as zf
import sys, time, re
import xml.etree.ElementTree as ET
from tinydb import TinyDB, where
import pprint as pp

from xbrl import XBRLParser, GAAP, GAAPSerializer
import logging
logging.basicConfig(format='  ---- %(filename)s|%(lineno)d ----\n%(message)s', level=logging.DEBUG)

db = TinyDB('db.json')
default_period_tag = "{http://www.xbrl.org/2003/instance}period"
default_explicit_member_tag = "{http://xbrl.org/2006/xbrldi}explicitMember"

def print_attributes(obj):
    for attribute in dir(obj):
        if not attribute.startswith("_"):
            logging.info(attribute)
            logging.info(type(attribute))
            logging.info(getattr(obj, attribute))
            # if type(attribute) is "class":
            #     print_attributes(attribute)


def element_walk(element, count=0):
    for child in element:
        print("\t"*count + str(child))
        if len(child):
            element_walk(child, count = count + 1)

def zip_contents(zipfile):
    return zf.ZipFile(zipfile, 'r')

def return_xbrl_tree_and_namespace(zipfile):
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
    # pp.pprint(ns)
    return [tree, ns, ticker]

def return_verbose_xbrl_dict(xbrl_tree, namespace, ticker):
    tree = xbrl_tree
    root = tree.getroot()
    ns = namespace
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

            context_element_dict[short].update({period: context_element.text})
            # context_element_dict["period"] = period

            fact_dict[context_id_short + ":" + short] = context_element_dict

        ticker_dict = {ticker: fact_dict}
        return(ticker_dict)

def return_simple_xbrl_dict(xbrl_tree, namespace, ticker):
    tree = xbrl_tree
    root = tree.getroot()
    ns = namespace
    reverse_ns = {v: k for k, v in ns.items()}

    context_element_list = tree.findall("xbrli:context", ns)
    for element in context_element_list:
        # pp.pprint(element.get("id"))
        pass

    all_facts_dict = {}
    for element in context_element_list:
        period_dict = {}
        dimension = None
        dimension_value = None
        previous_entry = None
        # print([x for x in element.iter()])
        # get period first:
        period_element = element.find(default_period_tag)
        for item in period_element.iter():
            if "startDate" in item.tag:
                period_dict["startDate"] = item.text
            elif "endDate" in item.tag:
                period_dict["endDate"] = item.text
            elif "instant" in item.tag:
                period_dict["instant"] = item.text
            elif "forever" in item.tag:
                period_dict["forever"] = item.text
        if not period_dict:
            logging.error("No period")
        else:
            logging.warning(period_dict)

        if period_dict.get("startDate"):
            period_serialized = period_dict.get("startDate") + ":" + period_dict.get("endDate")
        elif period_dict.get("instant"):
            period_serialized = period_dict.get("instant")
        elif period_dict.get("forever"):
            period_serialized = period_dict.get("forever")
        else:
            logging.error("no period_serialized")
            period_serialized = None


        context_id = element.get("id")
        context_ref_list = [x for x in root if x.get("contextRef") == context_id]
        pp.pprint(len(context_ref_list))
        if len(context_ref_list) > 2:
            for context_element in context_ref_list:
                if "TextBlock" in str(context_element.tag):
                    # logging.warning(context_element)
                    continue
                elif "&lt;" in str(context_element.text):
                    # logging.warning(context_element)
                    continue
                elif "<div " in str(context_element.text) and "</div>" in str(context_element.text):
                    # logging.warning(context_element)
                    continue

                tag = context_element.tag
                split_tag = tag.split("}")
                if len(split_tag) > 2:
                    logging.error(split_tag)
                institution = reverse_ns.get(split_tag[0][1:])
                accounting_item = split_tag[1]
                value = context_element.text
                unitRef = context_element.get("unitRef")
                decimals = context_element.get("decimals")
                if not all_facts_dict.get(institution):
                    logging.warning(institution)
                    all_facts_dict[institution] = {accounting_item: {period_serialized: {"value": value}}}
                    all_facts_dict[institution][accounting_item][period_serialized].update({"unitRef": unitRef})
                    all_facts_dict[institution][accounting_item][period_serialized].update({"decimals": decimals})
                elif all_facts_dict[institution].get(accounting_item) is None:
                    # logging.warning(accounting_item)
                    all_facts_dict[institution][accounting_item] = {period_serialized: {"value": value}}
                    all_facts_dict[institution][accounting_item][period_serialized].update({"unitRef": unitRef})
                    all_facts_dict[institution][accounting_item][period_serialized].update({"decimals": decimals})
                else:
                    logging.warning("hmm")
                    all_facts_dict[institution][accounting_item].update({period_serialized: {"value": value}})
                    all_facts_dict[institution][accounting_item][period_serialized].update({"unitRef": unitRef})
                    all_facts_dict[institution][accounting_item][period_serialized].update({"decimals": decimals})
        else:
            logging.warning("hrm")




        for item in element.findall(default_explicit_member_tag):
            dimension = item.attrib.get("dimension")
            dimension_value = item.text
            previous_entry = all_facts_dict.get(dimension)
            if previous_entry != dimension_value:
                logging.error("differing dimension values")




    ticker_dict = {ticker: all_facts_dict}
    # pp.pprint(ticker_dict)
    with open('output{}.txt'.format(ticker), 'wt') as out:
        pp.pprint(ticker_dict, stream=out)
    return(ticker_dict)

def save_ticker_dict(ticker_dict, db=db):
    ticker = ticker_dict.keys()[0]
    stock = db.get(ticker)

    institution_list = list(ticker_dict.values())
    for institution in list(ticker_dict.values()):
        print(institution)
        stock_institution = stock.get(institution)
        if not stock_institution:
            stock[institution] = list(institution.values())[0]
            continue
        for accounting_item in list(institution.values()):
            stock_accounting_item = stock_institution.get(accounting_item)
            if not stock_accounting_item:
                stock[institution][accounting_item] = list(accounting_item.values())[0]
                continue
            for period in list(accounting_item.values()):
                stock[institution][accounting_item][period] = list(period.values())[0]

def print_stock_dict(xbrl_dict, level=0):
    for key, value in xbrl_dict.items():
        #print("."*level)
        #pp.pprint(key)
        if isinstance(value, dict) or isinstance(value, list):
            if isinstance(value, dict):
                if len(value.values()) == 1:
                    #pp.pprint(value)
                    pass
                else:
                    print_stock_dict(value, level = level + 1)
            elif isinstance(value, list):
                for subvalue in value:
                    if isinstance(subvalue, dict):
                        print_stock_dict(subvalue, level = level + 1)
                    else:
                        #pp.pprint(subvalue)
                        pass
            else:
                #pp.pprint(value)
                pass
        else:
            #pp.pprint(value)
            pass


files = ["aro111.zip",
         "ge10.zip",
         "ge28.zip",
         "ge53.zip",
         "ge73.zip",
        ]
one_file = ["aro111.zip"]

from itertools import islice

def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(islice(iterable, n))
number_of_items = 5
start = time.time()
logging.info(start)





for file in one_file:
    tree, ns, ticker = return_xbrl_tree_and_namespace(file)
    stock_dict = return_simple_xbrl_dict(tree, ns, ticker)
    print_stock_dict(stock_dict)


stop = time.time()
logging.info(stop)














