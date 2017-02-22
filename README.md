# pymart usage

This API wrapper is still unfinished, but is still very useful.  I am using it currently.  Feel free to contribute.

To begin using the API, you will need your `private_key`, `consumer_id` and `channel_type`.  These are all provided by walmart once you have a seller account.

## Retrieve Item Information
We can ask for single item information, or for information in bulk.

#### Single Item
```python
import pymart
w = pymart.Walmart(private_key, consumer_id, channel_type)
r = w.get_item('some_sku_123')
r.content       # The xml data string
```
I'm using the requests library to make requests, and what is returned is the Request object.

#### Bulk Item
```python
import pymart
w = pymart.Walmart(private_key, consumer_id, channel_type)
r = w.get_all_items(offset=0, limit=20)
r.content       # The xml data string
```
You will have to do this many times to get all of your items, if you have many of them.

#### Bulk Item (with feeds)
We can also get our items and information from a feed, which returns a csv file.
```python
import pymart
w = pymart.Walmart(private_key, consumer_id, channel_type)
r, data = w.get_item_report(cleaned=True)
# data looks something like [[headers], [row], [row], ...]
```
Here, `r` is again the Request object, and data is a list of lists.  It looks like what would be returned by `csv.reader(f)`.

## Orders
Similarly, we can retrieve order information.
#### Single Order
```python
import pymart
w = pymart.Walmart(private_key, consumer_id, channel_type)
r = w.get_order('123456789') # arg is purchase order id
r.content # xml data string
```

#### Bulk Orders
For some reason, the Walmart API does not provide a way to filter orders by `modified_date`, so you'll have to do with `startCreatedDate` and `endCreatedDate`...
```python
import pymart
w = pymart.Walmart(private_key, consumer_id, channel_type)
r = w.get_all_orders(createdStartDate='<Some ISO 8601 DateTime>')
r.content # xml data string
```
If there are more than 200 orders in the response, then a `nextCursor` element will be provided and you can provide that as the sole argument to the `get_all_orders()` method to retrieve the next batch of orders.
There are more possible arguments to this method, take a look at the source if you need to filter your results further.

### Lastly
There are a few more methods I have provided that will return an XML data string through `r.content`. I would suggest just looking through the source code of `pymart.py`.  It's pretty easy to read and add on to.  If you add onto it, just mimic how I "signed" the requests in other methods.  That authorization signature was the most annoying part of writing this wrapper.  Hope this is useful to someone.
