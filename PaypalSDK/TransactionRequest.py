from .core import PayPalHttpClient

from datetime import timedelta
from urllib.parse import quote

# The PayPal SDK rocks (not!) and will only supply 31 days of transactions
# at once. So the TransactionRequest is written to slice up the requested
# period into slices of this size.  
MAX_DAYS = 31 

# This is a property of the v1 API, thayt it supports no pages larger 
# than this. Put here as a configurable in case it changes. We of course
# want to request the maximum amount we can, we only wnat the transactions 
# between a ggiven dates to dumb to a CSV really, don't want touse more 
# requests than needed. 
MAX_PAGE_SIZE = 500

class TransactionRequest:
    '''
    A simple Request class based on the PayPal SDK. 
    '''
    def __init__(self, dt_from, dt_to, max_days=MAX_DAYS):
        self.verb = "GET"
        
        # Gotta love PayPal (not), but they'll only return maximally 31 days of
        # transactions per request. So we split this into chunks of no more than 
        # 31 days to perform, you guessed it, multiple requests as if it were 
        # one. See self.execute(client) in which we sort of reverse the notion
        # of client.execute(request) to pull this trick.
        dt_from = dt_from.replace(microsecond=0)
        dt_to = dt_to.replace(microsecond=0)
        
        self.slices = []
        dt_slice = dt_from
        while dt_slice < dt_to:
            start = dt_slice
            end =  min(start + timedelta(days=max_days), dt_to) 
            self.slices.append(f"start_date={quote(start.isoformat())}&end_date={quote((end-timedelta(seconds=1)).isoformat())}")
            dt_slice = end

        self.path_root = f"/v1/reporting/transactions?fields=all&page_size={MAX_PAGE_SIZE}&"
        self.path = self.path_root + self.slices[0]
        self.headers = {}
        self.headers["Content-Type"] = "application/json"
        self.body = None
        
    def execute(self, client=None, environment=None):
        if not client:
            if not environment:
                raise Exception("To execute a TransactionRequest a client or evironment must be provided.")
            else:
                client = PayPalHttpClient(environment)

        prior_balance = None 
        transactions = []
        for slice in self.slices:  # @ReservedAssignment
            # We support slices, so that the caller can tweak the cyclical calls
            # But PayPal themsleves have a page_siaz, which defaults to 100 and has
            # a maximum value of 500, and will truncate a request to that count
            # frustratingly. We have ZERO reason to use less than the maximum but
            # in case there are more transactions in the slice than 500 we need an
            # inner loop over pages.

            # Repeat Until ...     
            page = 0
            while True: 
                self.path = self.path_root + slice + f"&page={page+1}"
                response = client.execute(self)
                
                page = response.result.page
                pages = response.result.total_pages
                
                for t in response.result.transaction_details:
                    if prior_balance is None:
                        prior_balance =  float(t.transaction_info.ending_balance.value)
                    else:
                        amount = float(t.transaction_info.transaction_amount.value)
                        fee_amount = getattr(t.transaction_info, "fee_amount", None)
                        fee = float(fee_amount.value) if fee_amount else 0
                        balance =  float(t.transaction_info.ending_balance.value)
                        expected_balance = round(prior_balance + amount + fee, 2)

                        # If the balance is not as expected that's a pretty 
                        # HUGE problem! This is an integrity check on the results
                        # and has helped find issues with the paging for example.                         
                        if not balance == expected_balance:
                            raise Exception("Balance mismatch in transactions provided by PayPal.")
                        else:
                            prior_balance = balance
                    
                    transactions.append(t)
                
                if page >= pages:
                    break
                
        return transactions