import zipfile as zf
import sys, time, re, datetime, json
import xml.etree.ElementTree as ET
from tinydb import TinyDB, where
import pprint as pp

from xbrl import XBRLParser, GAAP, GAAPSerializer
import logging
logging.basicConfig(format='  ---- %(filename)s|%(lineno)d ----\n%(message)s', level=logging.DEBUG)

db = TinyDB('db.json')
default_period_tag = "{http://www.xbrl.org/2003/instance}period"
default_explicit_member_tag = "{http://xbrl.org/2006/xbrldi}explicitMember"

GLOBAL_STOCK_DICT_LIST = []

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        elif isinstance(obj, datetime.date):
            return obj.isoformat()
        elif isinstance(obj, datetime.timedelta):
            return (datetime.datetime.min + obj).time().isoformat()

def return_stock_if_it_exists(ticker):
    for stock_dict in GLOBAL_STOCK_DICT_LIST:
        for key in stock_dict.keys():
            if key == ticker:
                return stock_dict

def iso_date_to_datetime(date_str):
    date_str = date_str.replace('"', "").replace("'","")
    return datetime.date(int(date_str.split("-")[0]), int(date_str.split("-")[1]), int(date_str.split("-")[2]))

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
        # print("\t"*count + str(child))
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

def return_verbose_xbrl_dict_broken(xbrl_tree, namespace, ticker):
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

    xbrl_stock_dict = return_stock_if_it_exists(ticker)
    if not xbrl_stock_dict:
        xbrl_stock_dict = {ticker: {}}
        GLOBAL_STOCK_DICT_LIST.append(xbrl_stock_dict)
    today = datetime.date.today()
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
            # logging.warning(period_dict)
            pass

        # datetime YYYY-MM-DD
        datetime_delta = None
        start_date = None
        if period_dict.get("startDate"):
            start_date = period_dict.get("startDate")
            end_date = period_dict.get("endDate")
            period_serialized = start_date + ":" + end_date
            start_datetime = iso_date_to_datetime(start_date)
            end_datetime = iso_date_to_datetime(end_date)
            datetime_delta = end_datetime - start_datetime
            datetime_to_save = end_datetime
        elif period_dict.get("instant"):
            instant = period_dict.get("instant")
            period_serialized = instant
            instant_datetime = iso_date_to_datetime(instant)
            datetime_to_save = instant_datetime
        elif period_dict.get("forever"):
            forever = period_dict.get("forever")
            period_serialized = forever
            forever_datetime = iso_date_to_datetime(forever)
            datetime_to_save = forever_datetime
        else:
            logging.error("no period_serialized")
            period_serialized = None
            datetime_to_save = None

        context_id = element.get("id")
        context_ref_list = [x for x in root if x.get("contextRef") == context_id]
        # pp.pprint(len(context_ref_list))
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
            if not xbrl_stock_dict[ticker].get(institution):
                # logging.warning(institution)
                xbrl_stock_dict[ticker][institution] = {accounting_item: {period_serialized: {"value": value}}}
                period_dict = xbrl_stock_dict[ticker][institution][accounting_item][period_serialized]
                period_dict.update({"datetime": DateTimeEncoder().encode(datetime_to_save)})
                period_dict.update({"timedeltastart": DateTimeEncoder().encode(start_date)})
                period_dict.update({"unitRef": unitRef})
                period_dict.update({"decimals": decimals})
            elif xbrl_stock_dict[ticker][institution].get(accounting_item) is None:
                # logging.warning(accounting_item)
                xbrl_stock_dict[ticker][institution][accounting_item] = {period_serialized: {"value": value}}
                period_dict = xbrl_stock_dict[ticker][institution][accounting_item][period_serialized]
                period_dict.update({"datetime": DateTimeEncoder().encode(datetime_to_save)})
                period_dict.update({"timedeltastart": DateTimeEncoder().encode(start_date)})
                period_dict.update({"unitRef": unitRef})
                period_dict.update({"decimals": decimals})
            else:
                xbrl_stock_dict[ticker][institution][accounting_item].update({period_serialized: {"value": value}})
                period_dict = xbrl_stock_dict[ticker][institution][accounting_item][period_serialized]
                period_dict.update({"datetime": DateTimeEncoder().encode(datetime_to_save)})
                period_dict.update({"timedeltastart": DateTimeEncoder().encode(start_date)})
                period_dict.update({"unitRef": unitRef})
                period_dict.update({"decimals": decimals})

            accounting_item_dict = xbrl_stock_dict[ticker][institution][accounting_item]
            most_recent_index = None
            most_recent_dict = accounting_item_dict.get("most_recent")
            if most_recent_dict:
                most_recent_index = most_recent_dict.get("period")
            if not most_recent_index:
                accounting_item_dict.update({"most_recent": {"period": period_serialized}})
                if datetime_delta:
                    if datetime_delta >= datetime.timedelta(days=360) and datetime_delta < datetime.timedelta(days=370):
                        accounting_item_dict["most_recent"].update({"year": period_serialized})
                    elif datetime_delta > datetime.timedelta(days=85) and datetime_delta < datetime.timedelta(days=95):
                        accounting_item_dict["most_recent"].update({"quarter": period_serialized})
                    elif datetime_delta >= datetime.timedelta(days=28) and datetime_delta <= datetime.timedelta(days=31):
                        accounting_item_dict["most_recent"].update({"month": period_serialized})

            else: # there is a most recent
                if datetime_to_save:
                    existing_entry = accounting_item_dict[most_recent_index]
                    existing_datetime = existing_entry.get("datetime")
                    if existing_datetime:
                        existing_datetime = iso_date_to_datetime(existing_datetime)
                        if datetime_to_save > existing_datetime:
                            accounting_item_dict.update({"most_recent": {"period": period_serialized}})

                    #existing_timedelta = existing_entry.get("timedeltastart")
                    if datetime_delta:
                        if datetime_delta >= datetime.timedelta(days=360) and datetime_delta < datetime.timedelta(days=370):
                            existing_timedelta_index = accounting_item_dict["most_recent"].get("year")
                            if existing_timedelta_index:
                                existing_timedelta_date = accounting_item_dict[existing_timedelta_index].get("datetime")
                                existing_timedelta_date = iso_date_to_datetime(existing_timedelta_date)
                                if datetime_to_save > existing_timedelta_date:
                                    accounting_item_dict["most_recent"].update({"year": period_serialized})
                            else:
                                accounting_item_dict["most_recent"].update({"year": period_serialized})
                        elif datetime_delta > datetime.timedelta(days=85) and datetime_delta < datetime.timedelta(days=95):
                            existing_timedelta_index = accounting_item_dict["most_recent"].get("quarter")
                            if existing_timedelta_index:
                                existing_timedelta_date = accounting_item_dict[existing_timedelta_index].get("datetime")
                                existing_timedelta_date = iso_date_to_datetime(existing_timedelta_date)
                                if datetime_to_save > existing_timedelta_date:
                                    accounting_item_dict["most_recent"].update({"quarter": period_serialized})
                            else:
                                accounting_item_dict["most_recent"].update({"quarter": period_serialized})
                        elif datetime_delta >= datetime.timedelta(days=28) and datetime_delta <= datetime.timedelta(days=31):
                            existing_timedelta_index = accounting_item_dict["most_recent"].get("month")
                            if existing_timedelta_index:
                                existing_timedelta_date = accounting_item_dict[existing_timedelta_index].get("datetime")
                                existing_timedelta_date = iso_date_to_datetime(existing_timedelta_date)
                                if datetime_to_save > existing_timedelta_date:
                                    accounting_item_dict["most_recent"].update({"month": period_serialized})
                            else:
                                accounting_item_dict["most_recent"].update({"month": period_serialized})

        for item in element.findall(default_explicit_member_tag):
            dimension = item.attrib.get("dimension")
            dimension_value = item.text
            previous_entry = xbrl_stock_dict.get(dimension)
            if previous_entry != dimension_value:
                logging.error("differing dimension values")




    # pp.pprint(xbrl_stock_dict)
    with open('output{}.json'.format(ticker), 'wt') as output_file:
        json.dump(xbrl_stock_dict, output_file, indent=4)
    return(xbrl_stock_dict)

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


for file in files:
    tree, ns, ticker = return_xbrl_tree_and_namespace(file)
    stock_dict = return_simple_xbrl_dict(tree, ns, ticker)
    print_stock_dict(stock_dict)


stop = time.time()
total = stop-start
logging.info(total)














