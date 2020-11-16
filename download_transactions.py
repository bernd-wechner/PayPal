#!/usr/bin/env python3
import sys, os, json

from PaypalSDK.core import PayPalHttpClient, LiveEnvironment
from PaypalSDK import TransactionRequest

from appdirs import user_config_dir
from dateutil import tz 
from dateutil.parser import parse as parse_date
from fiscalyear import setup_fiscal_calendar, FiscalDateTime, FiscalYear

if not os.path.exists(user_config_dir("PayPal")):
    os.makedirs(user_config_dir("PayPal"))
    
cred_file  = os.path.join(user_config_dir("PayPal"), "sdk_credentials.json")

CREDS = {}
if os.path.isfile(cred_file):
    with open(cred_file, "r") as file:
        CREDS = json.loads(file.read())

if not CREDS:
    with open(cred_file, "w") as file:
        file.write(json.dumps({"ID": "<your PayPal client ID here>", "Secret": "<your PayPal secret here>"}))

    print("No PayPal SDK credentials available. Please add credentials details to {cred_file}", file=sys.stderr)

else:
    # Creating an environment
    environment = LiveEnvironment(client_id=CREDS["ID"], client_secret=CREDS["Secret"])
    client = PayPalHttpClient(environment)
    
    setup_fiscal_calendar(start_month=7)
    dt_from = FiscalYear(FiscalDateTime.now().fiscal_year).start.astimezone(tz.tzlocal())
    dt_to = FiscalDateTime.now().astimezone(tz.tzlocal())
        
    request = TransactionRequest(dt_from, dt_to)
     
    transactions = request.execute(client)
    
    header = ["Date", 
              "Transaction Commodity", 
              "Deposit", 
              "Price", 
              "Quantity", 
              "Balance", 
              "Num", 
              "Description", 
              "Notes", 
              "Transfer Account"]
    print(", ".join(header))        
    
    for t in transactions: #response.result.transaction_details:
        id = t.transaction_info.transaction_id  # @ReservedAssignment
        note = getattr(t.transaction_info, "transaction_note", "")
        idate = parse_date(t.transaction_info.transaction_initiation_date).astimezone(tz.tzlocal()).strftime("%Y-%m-%d")
        udate =  parse_date(t.transaction_info.transaction_updated_date).astimezone(tz.tzlocal()).strftime("%Y-%m-%d")
        amount = float(t.transaction_info.transaction_amount.value)
        currency = t.transaction_info.transaction_amount.currency_code
        balance =  float(t.transaction_info.ending_balance.value)
        bcurrency =  t.transaction_info.ending_balance.currency_code
    
        fee_amount = getattr(t.transaction_info, "fee_amount", None)
        fee = float(fee_amount.value) if fee_amount else 0
        fcurrency = t.transaction_info.fee_amount.currency_code if fee else ""
        
        # The PayPal Commission on the transaction
        # cart items don't know this so we have to 
        # work it out at the transaction level and 
        # apply it to cart items.
        pp_commission = fee/amount
        
        deposit = amount * (1+pp_commission)
        
        cart = t.cart_info
        if hasattr(cart, "item_details"):
            wait_for_amount = False
            for item in cart.item_details:
                try:
                    name = getattr(item, "item_name", "")
                    if wait_for_amount:
                        if not name == "Amount":
                            raise Exception("Oops: Expecting an Amount item following a transaction without an amount and didn't find one.")                    
                    else:    
                        quantity = item.item_quantity
    
                    # PayPal transaction exhibit one gran weirdness at least
                    # Typically each item in the cart as an item_amount 
                    # BUT sometimes this is missing. if that's the case 
                    # the next item in the cart will be named "Amount"
                    # and provide the amount. Go figure.                  
                    if hasattr(item, "item_amount"):
                        amount = float(item.item_amount.value)
                        deposit = amount * (1+pp_commission)
                        currency = item.item_amount.currency_code
                        wait_for_amount = False
                    elif wait_for_amount:
                        # If w're waiting for an amount, we should have
                        # got one. It's a problem if not.
                        raise Exception("Oops: Was waiting for an Amount item, it came, but didn't actually contain an amount!")                    
                    else:
                        wait_for_amount = True
                        continue
                        
                except Exception as E:
                    breakpoint()
    
                summary = [idate, 
                          f"CURRENCY::{currency}", 
                          f"{deposit:.2f}", 
                          f"{amount:.2f}", 
                          quantity, 
                          f"{balance:.2f}", 
                          id, 
                          name.strip(), 
                          note.strip()]
                
                print(",".join(summary))        
        else:
            summary = [idate, 
                      f"CURRENCY::{currency}", 
                      f"{deposit:.2f}", 
                      f"{amount:.2f}", 
                      "1", 
                      f"{balance:.2f}", 
                      id, 
                      "", 
                      note.strip()]
            print(",".join(summary))        
