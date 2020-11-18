# PayPal Transaction Downloader for GnuCash Imports

Long story short, the PayPal CSV downloads suck. They are missing vital information about the transactions, notably the breakdown of what people purchased.

So turned to the PayPal SDK to see if it could do better.

The PayPal SDK sucks! Well it works, but the documentation and support is a literal schmozzle. 

That said, it works, and I can now download a full transaction history with a breakdown of what was purchased.

This is the software as it stands. 

To use it you need PayPal credentials:

https://developer.paypal.com/docs/api/overview/#get-credentials

It is based on:

- The core API that is offered in two distinct PayPal repos
	- https://github.com/paypal/Checkout-Python-SDK	
	- https://github.com/paypal/Payouts-Python-SDK
	- For whatever stupid reason rather than provide an SDK they wrote a "core" and it appears almost identially in a Checkout SDK and a Payouts SDK, whatever they do ...
- Documentation on teh Transaction API:
	- https://developer.paypal.com/docs/integration/direct/transaction-search/#list-transactions
	- https://developer.paypal.com/docs/api/transaction-search/v1/

But of course it doesn't work as documented and there is odd confusion between the deprecated v1 API and the new v2 API but there is zip info on transactionlisting or downloading with v2 (only Pyaouts and Checkouts as above) and the demos all use the v1.

- https://developer.paypal.com/docs/api/quickstart/install/

All I can say is: Aaaargh! PayPal sure have a schmozzle of API and SDK documentation and offerings and itcost me way more efort than it should to get the transaction downloads I want, BUT:

- It works and is way better than requesting downloads through their website because:
	- It comes immediately, (on their website you request them and on good days they ar eprepared and ready for download quikcly, on bad days it takes hours before you get na email that it can be downloaded)
	- It includes a breakdown of the shopping cart items (which their website CSV donwloads do not!
	- It can include (not implemented in the current draft I have here) much more information about the buyer than their standard CSV donwloads offer. 

Of course it's current as at Novemebr 2020 and PayPal are evolving their API so may change and we are leaning onthe deprecated v1 API, because there is no evidence of a v2 support for same yet. But I do hope you get some use out of this too if you landed here. 
