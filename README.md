# ezmysql - Easy way to use mysql in modes of `sync` and `async`

A lightweight wrapper around pymysql (synchronous) and aiomysql (asynchronous)
for reading and writing MySQL database easily.

It support two modes: Synchronous and Asynchronous. Please select the mode on
your need. The two different modes has the same interface (functions), which
makes you just learn one but to use both of them.


# Installation

from pypi: `pip install ezmysql`

from source:
``` bash
git clone https://github.com/veelion/ezmysql`
cd ezmysql
python setup.py install
```

# Usage:

There are two types of methods to operate MySQL: read and write
Methods to read:
* connection.query(): to get a list of rows from a table
* connection.get(): to get a dict of one row from a table

Methods to write:
* connection.execute(): to execute a write operation sql, return the last row_id
  if available

Hihg level methods to operate one table:
* connection.table_has(): to check whether has the condition record
* connection.table_insert(): to insert a row(dict) to the table
* connection.table_update(): to update the table with condition

# For example:

``` python
from ezmysql import ConnectionSync

def main():
    host = 'localhost'
    database = 'testdb'
    user = 'your-user'
    password = 'your-password'
    # create connection
    db = ConnectionSync(
        host,
        database,
        user,
        password,
    )
    
    ## db.execute()...
    sql = "insert into simple(title, text) values(%s, %s)"
    title = 'ezultramysql'
    text = 'text\nez\r\nultramysql%%\\123,item of the first'
    r = db.execute(sql, title, text)
    row = db.get('select * from simple where id=%s' % r)
    assert row['title'] == title
    assert row['text'] == text

    print('## test WARNING-0')
    sql = 'update simple set title="%s" where id=1'
    r = db.execute(sql, 'apple')
    row = db.get('select title from simple where id=1')
    print('%s != %s' % (row['title'], 'apple'))
    assert row['title'] != 'apple'

    print('\n## db.get()...')
    row = db.get('select * from simple limit %s', 1)
    for k, v in row.items():
        print('%s:%s' % (k,v))

    print('\n## high-level interface testing...')
    g = db.table_has('simple', 'id', 3)
    print('is_ in:', g)
    bin_zip = 'this is zlib to compress string'
    updates = {
        'title': 'by_"update"_table()',
        'text': 'by_update_table()\n\rzzz',
        'length': 123,
        'bin': zlib.compress(bin_zip.encode('utf8'))
    }
    r = db.table_update('simple', updates, 'id', 1)
    print('update_table:', r)
    r = db.get('select * from simple where id=1')
    assert r['title'] == updates['title']
    assert r['text'] == updates['text']
    assert bin_zip == zlib.decompress(r['bin']).decode('utf8')

    print('\n## db.query()...')
    rows = db.query('select * from simple where text like %s limit %s', '%item%', 10)
    for r in rows:
        for k, v in r.items():
            print('%s: %s' % (k, v))
        print('======================')
    db.close()
    print('testing succeed!')

if __name__ == '__main__':
    main()
```

For details of synchronous, to see [examples/sync_example.py](examples/sync_example.py)

For details of Asynchronous, to see [examples/async_example.py](examples/async_example.py)


# USING NOTES:
``` bash
    0. Don not quote the '%s' in sql, ezmysql will process it, e.g.
        Bad:
            sql = 'update tbl set title="%s" where id=1'
            sql = 'insert into tbl(title, author) values("%s", "%s")'
        Good:
            sql = 'update tbl set title=%s where id=1'
            sql = 'insert into tbl(title, author) values(%s, %s)'
    1. ezmysql will do escape_string job for MySQL,
       you don't need to warry about it
    2. It sets the character encoding to UTF-8 by default
       on all connections to avoid encoding errors.
```
