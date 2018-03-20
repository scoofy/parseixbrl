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


class Stock(persistent.Persistent):
    def __init__(self, symbol, firm_name = ""):
        self.held_list = persistent.list.PersistentList()
        # held list should take certain values into account
        # account where stock is held
        # number of shares held in that account
        # redundant information seems silly,
        # could keep the shares in the account obj only.

        # Ticker Symbol Key
        #               Class "X"   Preferred   Warrents (currently ignored)
        # wxStocks      ".X"        ".PX"       Ignored
        #
        # Nasdaq        "/X"        "^X"        "/WS","/WS/"
        # Morningstar   ".X"        "PRX"       ?
        # Yahoo         "-X"        "-PX"       "-WT"
        # AAII          ".X"        " PR"       ?
        # not yet implimented
        # Bloomberg     "/X"        "/PX"       ?
        # Google        ?           "-X"        ?

        symbol = symbol.upper()
        if symbol.isalpha():
            self.symbol = symbol

            self.nasdaq_symbol = symbol
            self.aaii_symbol = symbol
            self.yahoo_symbol = symbol
            self.morningstar_symbol = symbol

            self.yql_ticker = symbol
        elif ("." in symbol) or ("^" in symbol) or ("/" in symbol) or ("-" in symbol) or (" PR" in symbol):
            if "." in symbol:
                if ".P" in symbol:
                    # preferred
                    self.symbol = symbol

                    self.nasdaq_symbol = symbol.replace(".P", "^")
                    self.yahoo_symbol = symbol.replace(".P", "-P")
                    self.morningstar_symbol = symbol.replace(".P", "PR")
                    self.aaii_symbol = symbol.replace(".P", " PR")

                    self.yql_ticker = symbol.replace(".P", "-P")
                else:
                    # CLASS.X shares:
                    self.symbol = symbol
                    self.ticker = symbol

                    self.aaii_symbol = symbol
                    self.morningstar_symbol = symbol
                    self.nasdaq_symbol = symbol.replace(".", "/")
                    self.yahoo_symbol = symbol.replace(".", "-")

                    self.yql_ticker = symbol.replace(".", "-")
            if "^" in symbol:
                # Nasdaq preferred
                self.symbol = symbol.replace("^", ".P")

                self.nasdaq_symbol = symbol
                self.yahoo_symbol = symbol.replace("^", "-P")
                self.morningstar_symbol = symbol.replace("^", "PR")
                self.aaii_symbol = symbol.replace("^", " PR")

                self.yql_ticker = symbol.replace("^", "-P")
            if "/" in symbol:
                # Warrants currently ignored but this function should be reexamined if warrents to be included in the future
                # if "/WS" in symbol:
                #   # Nasdaq Warrent
                #   if "/WS/" in symbol:
                #       # more complicated version of the same thing
                #       self.nasdaq_symbol = symbol
                #       self.yahoo_symbol = symbol.replace("/WS/","-WT")
                #       # I don't know how morningstar does warrents
                #   else:
                #       self.nasdaq_symbol = symbol
                #       self.yahoo_symbol = symbol.replace("/WS","-WT")
                #   self.aaii_symbol = None

                # If bloomberg is integrated, this will need to be changed for preferred stock
                # if "/P" in symbol:
                #   pass

                # Nasdaq class share
                self.symbol = symbol.replace("/", ".")

                self.nasdaq_symbol = symbol
                self.aaii_symbol = symbol.replace("/", ".")
                self.morningstar_symbol = symbol.replace("/", ".")
                self.yahoo_symbol = symbol.replace("/", ".")

                self.yql_ticker = symbol.replace("/", ".")
            if "-" in symbol:
                if "-P" in symbol:
                    # Yahoo preferred
                    self.symbol = symbol.replace("-P", ".P")


                    self.yahoo_symbol = symbol
                    self.nasdaq_symbol = symbol.replace("-P", "^")
                    self.aaii_symbol = symbol.replace("-P", " PR")
                    self.morningstar_symbol = symbol.replace("-P", "PR")

                    self.yql_ticker = symbol
                else:
                    # Yahoo Class
                    self.symbol = symbol.replace("-", ".")


                    self.yahoo_symbol = symbol
                    self.nasdaq_symbol = symbol.replace("-", "/")
                    self.aaii_symbol = symbol.replace("-", ".")
                    self.morningstar_symbol = symbol.replace("-", ".")

                    self.yql_ticker = symbol
            if " PR" in symbol:
                # AAII preferred
                self.symbol = symbol.replace(" PR", ".P")


                self.aaii_symbol = symbol
                self.yahoo_symbol = symbol.replace(" PR", "-P")
                self.nasdaq_symbol = symbol.replace(" PR", "^")
                self.morningstar_symbol = symbol.replace(" PR", "PR")

                self.yql_ticker = symbol.replace(" PR", "-P")

        # Finally:
        # if morningstar preferred notation "XXXPRX", i don't know how to fix that since "PRE" is a valid ticker

        elif "_" in symbol:
            self.symbol = symbol

            self.nasdaq_symbol = None
            self.aaii_symbol = symbol
            self.yahoo_symbol = None
            self.morningstar_symbol = None
            self.yql_ticker = None

        else: #something is very broken, and must be fixed immediately
            logging.error("illegal ticker symbol: {}, {}\nThe program will now close without saving, you need to add this to the wxStocks_classes exceptions list immediately.".format(symbol, firm_name))
            sys.exit()

        self.ticker = self.symbol
        self.firm_name = firm_name

        self.epoch = float(time.time())
        self.created_epoch = float(time.time())
        self.updated = datetime.datetime.now()

        # updates

        self.last_nasdaq_scrape_update = 0.0

        self.last_yql_basic_scrape_update = 0.0

        self.last_balance_sheet_update_yf = 0.0
        self.last_balance_sheet_update_ms = 0.0

        self.last_cash_flow_update_yf = 0.0
        self.last_cash_flow_update_ms = 0.0

        self.last_income_statement_update_yf = 0.0
        self.last_income_statement_update_ms = 0.0

        self.last_key_ratios_update_ms = 0.0

        self.last_aaii_update_aa = 0.0

    def testing_reset_fields(self):
        self.last_yql_basic_scrape_update = 0.0

        self.last_balance_sheet_update_yf = 0.0
        self.last_balance_sheet_update_ms = 0.0

        self.last_cash_flow_update_yf = 0.0
        self.last_cash_flow_update_ms = 0.0

        self.last_income_statement_update_yf = 0.0
        self.last_income_statement_update_ms = 0.0

        self.last_key_ratios_update_ms = 0.0


GLOBAL_STOCK_LIST = []
GLOBAL_STOCK_DICT_LIST = []

def return_stock_if_it_exists(ticker):
    for stock_dict in GLOBAL_STOCK_LIST:
        if stock.ticker == ticker:
            return stock
    # else
    stock = Stock(ticker)
    return stock

def return_stock_dict_if_it_exists(ticker):
    for stock_dict in GLOBAL_STOCK_DICT_LIST:
        for key in stock_dict.keys():
            if key == ticker:
                return stock_dict

def iso_date_to_datetime(date_str):
    # date_str = date_str.replace('"', "").replace("'","")
    return datetime.date(int(date_str.split("-")[0]), int(date_str.split("-")[1]), int(date_str.split("-")[2]))


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

def return_simple_xbrl_dict(xbrl_tree, namespace, ticker):
    tree = xbrl_tree
    root = tree.getroot()
    ns = namespace
    reverse_ns = {v: k for k, v in ns.items()}

    context_element_list = tree.findall("xbrli:context", ns)
    for element in context_element_list:
        # pp.pprint(element.get("id"))
        pass

    xbrl_stock_dict = return_stock_dict_if_it_exists(ticker)
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
        if period_dict.get("startDate"):
            start_date = period_dict.get("startDate")
            end_date = period_dict.get("endDate")
            period_serialized = start_date + ":" + end_date
            start_datetime = iso_date_to_datetime(start_date)
            end_datetime = iso_date_to_datetime(end_date)
            datetime_delta = end_datetime - start_datetime
            datetime_to_save = end_datetime
            iso_date_to_save = end_date
            iso_start_date = start_date
        elif period_dict.get("instant"):
            instant = period_dict.get("instant")
            period_serialized = instant
            instant_datetime = iso_date_to_datetime(instant)
            datetime_to_save = instant_datetime
            iso_date_to_save = instant
        elif period_dict.get("forever"):
            forever = period_dict.get("forever")
            period_serialized = forever
            forever_datetime = iso_date_to_datetime(forever)
            datetime_to_save = forever_datetime
            iso_date_to_save = forever
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
            elif xbrl_stock_dict[ticker][institution].get(accounting_item) is None:
                # logging.warning(accounting_item)
                xbrl_stock_dict[ticker][institution][accounting_item] = {period_serialized: {"value": value}}
            else:
                xbrl_stock_dict[ticker][institution][accounting_item].update({period_serialized: {"value": value}})
            period_dict = xbrl_stock_dict[ticker][institution][accounting_item][period_serialized]
            period_dict.update({"datetime": iso_date_to_save})
            if datetime_delta:
                period_dict.update({"timedeltastart": iso_start_date})
            if unitRef:
                period_dict.update({"unitRef": unitRef})
            if decimals:
                period_dict.update({"decimals": decimals})

            accounting_item_dict = xbrl_stock_dict[ticker][institution][accounting_item]
            most_recent_index = None
            most_recent_dict = accounting_item_dict.get("most_recent")
            if most_recent_dict:
                most_recent_index = most_recent_dict.get("period")
            if not most_recent_index:
                accounting_item_dict.update({"most_recent": {"period": period_serialized}})
                if datetime_delta:
                    if datetime_delta >= datetime.timedelta(days=359) and datetime_delta < datetime.timedelta(days=370):
                        accounting_item_dict["most_recent"].update({"year": period_serialized})
                    elif datetime_delta > datetime.timedelta(days=85) and datetime_delta < datetime.timedelta(days=95):
                        accounting_item_dict["most_recent"].update({"quarter": period_serialized})
                    elif datetime_delta >= datetime.timedelta(days=27) and datetime_delta <= datetime.timedelta(days=32):
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
                        if datetime_delta >= datetime.timedelta(days=359) and datetime_delta < datetime.timedelta(days=370):
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
                        elif datetime_delta >= datetime.timedelta(days=27) and datetime_delta <= datetime.timedelta(days=32):
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

def save_stock_dict(xbrl_stock_dict, level=0):
    ticker = xbrl_stock_dict.keys()[0]
    stock = return_stock_if_it_exists(ticker)
    base_dict = xbrl_stock_dict[ticker]
    for institution in base_dict.keys():
        institution_dict = base_dict[institution]
        for accounting_item in institution_dict.keys():
            period_dict = institution_dict[accounting_item]
            period_dict_str = str(accounting_item) + "_" + str(institution) +  "_dict_" + "__us"
            setattr(stock, period_dict_str, period_dict)
            most_recent_dict = period_dict["most_recent"]
            if len(most_recent_dict.keys) > 2:
                for period in most_recent_dict.keys():
                    if period == "period":
                        continue
                    most_recent_period_ref = most_recent_dict[period]
                    value = period_dict[most_recent_period_ref]["value"]
                    period_str = str(accounting_item) + "_" + str(institution) +  "_most_recent_" + period + "__us"
                    setattr(stock, period_str, value)
            else: # only one unique period (this is normal)
                most_recent_period_ref = most_recent_dict["period"]
                value = period_dict[most_recent_period_ref]["value"]
                period_str = str(accounting_item) + "_" + str(institution) +  "_most_recent_period__us"
                setattr(stock, period_str, value)





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


stop = time.time()
total = stop-start
logging.info(total)














