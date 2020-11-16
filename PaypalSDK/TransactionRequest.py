from .core import PayPalHttpClient

from datetime import timedelta
from urllib.parse import quote

# The PayPal SDK rocks (not!) and will only supply 31 days of transactions
# at once. So the TransactionRequest is written to slice up the requested
# period into slices of this size.  
MAX_DAYS = 31 

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

        self.path_root = f"/v1/reporting/transactions?fields=all&"
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
                 
        transactions = []
        for slice in self.slices:  # @ReservedAssignment
            self.path = self.path_root + slice
            response = client.execute(self)
            for t in response.result.transaction_details:
                transactions.append(t)
                
        return transactions