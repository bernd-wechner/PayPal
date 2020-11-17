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
              "Partner", 
              "Transfer Account"]
    print(",".join(header))        
    
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
        
        if amount > 0:
            if hasattr(t, "payer_info"):
                email = getattr(t.payer_info, "email_address", "")
                name = getattr(t.payer_info.payer_name, "alternate_full_name", "")
                account_id = getattr(t.payer_info, "account_id", "")
                
#                 if not email and not name:
#                     breakpoint()
                
                address = ""
                if hasattr(t.payer_info, "address"):
                    addr = [
                        getattr(t.payer_info.address, "line1", "").replace("No Street Address Provided", ""),
                        getattr(t.payer_info.address, "city", "").replace("No City Provided", ""),
                        getattr(t.payer_info.address, "postal_code", ""),
                        getattr(t.payer_info.address, "state", ""),
                        getattr(t.payer_info.address, "country_code", "")
                        ]
                    
                    address = ". ".join(addr)
                
                partner = account_id
                partner += f" {name}" if name else ""
                partner += f" <{email}>" if email else ""
                partner = partner.strip()
                
                # The addresses the paypal SDK returns are 
                # complete nonsense. There's bug either at 
                # the server end or in the Python libs, but 
                # being a v1 API they claim no support for 
                # it any more. 
                #partner += " " + address.strip()
            else:
                partner = "unknown payer"
        else:
            partner = "unknown recipient"
            
        # The PayPal Commission on the transaction
        # cart items don't know this so we have to 
        # work it out at the transaction level and 
        # apply it to cart items.
        pp_commission = fee/amount
        
        deposit = amount * (1+pp_commission)
        
        cart = t.cart_info
        if hasattr(cart, "item_details"):
            wait_for_amount = False
            prior_item_name = None
            for item in cart.item_details:
                item_name = getattr(item, "item_name", "")
                if wait_for_amount:
                    if item_name == "Amount":
                        item_name = prior_item_name
                    else:
                        raise Exception("Oops: Expecting an Amount item following a transaction without an amount and didn't find one.")                    
                else:    
                    quantity = item.item_quantity
                    prior_item_name = item_name

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
                    
#                     if item_name == "Amount":
#                         breakpoint()
                        
                    summary = [idate, 
                              f"CURRENCY::{currency}", 
                              f"{deposit:.2f}", 
                              f"{amount:.2f}", 
                              quantity, 
                              f"{balance:.2f}", 
                              id, 
                              item_name.strip(), 
                              note.strip(),
                              partner]
                    
                    print(",".join(summary))        
                    
                elif wait_for_amount:
                    # If w're waiting for an amount, we should have
                    # got one. It's a problem if not.
                    raise Exception("Oops: Was waiting for an Amount item, it came, but didn't actually contain an amount!")                    
                else:
                    wait_for_amount = True
        else:
            summary = [idate, 
                      f"CURRENCY::{currency}", 
                      f"{deposit:.2f}", 
                      f"{amount:.2f}", 
                      "1", 
                      f"{balance:.2f}", 
                      id, 
                      "", 
                      note.strip(),
                      partner]
            print(",".join(summary))        
