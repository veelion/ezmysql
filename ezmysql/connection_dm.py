"""A lightweight wrapper around oracledb for easy to use
Only for python 3
"""

import time
import traceback
import dmPython


class ConnectionDM:
    def __init__(self, host, database, user, password,
                 port=5236,
                 max_idle_time=7*3600,
                 connect_timeout=10,
                 autocommit=True,
                 return_dict=True,
                 charset="utf8mb4"):
        self.max_idle_time = max_idle_time
        self._db_args = {
            'host': host,
            'user': user,
            'password': password,
            'autoCommit': autocommit,
        }
        if return_dict:
            self._db_args['cursorclass'] = dmPython.DictCursor
        self._autocommit = autocommit
        if port:
            self._db_args['port'] = port
        self._db = None
        self._last_use_time = time.time()
        self.reconnect()

    def _ensure_connected(self):
        if (self._db is None or
                (time.time() - self._last_use_time > self.max_idle_time)):
            self.reconnect()
        self._last_use_time = time.time()

    def _cursor(self):
        self._ensure_connected()
        return self._db.cursor()

    def __del__(self):
        self.close()

    def close(self):
        """Closes this database connection."""
        if getattr(self, "_db", None) is not None:
            if not self._autocommit:
                self._db.commit()
            self._db.close()
            self._db = None

    def reconnect(self):
        """Closes the existing database connection and re-opens it."""
        self.close()
        self._db = dmPython.connect(**self._db_args)

    def query(self, query, *parameters, **kwparameters):
        """Returns a row list for the given query and parameters."""
        cursor = self._cursor()
        try:
            cursor.execute(query, kwparameters or parameters)
            # if self._return_dict:
            #     columns = [col[0] for col in cursor.description]
            #     cursor.rowfactory = lambda *args: dict(zip(columns, args))
            #     # cursor.rowfactory = lambda *args: dict(zip(columns, [str(a) if isinstance(a, oracledb.LOB) else a for a in args]))
            #     # cursor.rowfactory = lambda *args: dict(zip(columns, map(str, args)))
            result = cursor.fetchall()
            return result
        finally:
            cursor.close()

    def get(self, query, *parameters, **kwparameters):
        """Returns the (singular) row returned by the given query.
        """
        cursor = self._cursor()
        try:
            cursor.execute(query, kwparameters or parameters)
            # if self._return_dict:
            #     columns = [col[0] for col in cursor.description]
            #     # cursor.rowfactory = lambda *args: dict(zip(columns, map(str, args)))
            #     # cursor.rowfactory = lambda *args: dict(zip(columns, [str(a) if isinstance(a, oracledb.LOB) else a for a in args]))
            #     cursor.rowfactory = lambda *args: dict(zip(columns, args))
            return cursor.fetchone()
        finally:
            cursor.close()

    def execute(self, query, *parameters, **kwparameters):
        """Executes the given query, returning the lastrowid from the query."""
        cursor = self._cursor()
        try:
            cursor.execute(query, kwparameters or parameters)
            if self._autocommit:
                self._db.commit()
            return cursor.lastrowid
        except Exception as e:
            if e.args[0] == 1062:
                # just skip duplicated item error
                pass
            else:
                traceback.print_exc()
                raise e
        finally:
            cursor.close()

    insert = execute

    # =============== high level method for table ===================

    def table_has(self, table_name, field, value):
        sql = 'SELECT {} FROM {} WHERE {}="{}"'.format(
            field,
            table_name,
            field,
            value)
        d = self.get(sql)
        return d

    def table_insert(self, table_name, item):
        '''item is a dict : key is mysql table field'''
        fields = list(item.keys())
        values = list(item.values())
        fieldstr = ','.join(fields)
        valstr = ','.join(['%s'] * len(item))
        sql = 'INSERT INTO {} ({}) VALUES({})'.format(
            table_name, fieldstr, valstr)
        try:
            last_id = self.execute(sql, *values)
            return last_id
        except Exception as e:
            print(e)
            if e.args[0] == 1062:
                # just skip duplicated item error
                pass
            else:
                traceback.print_exc()
                print('sql:', sql)
                print('item:')
                for i in range(len(fields)):
                    vs = str(values[i])
                    if len(vs) > 300:
                        print(fields[i], ' : ', len(vs), type(values[i]))
                    else:
                        print(fields[i], ' : ', vs, type(values[i]))
                raise e

    def table_insert_many(self, table_name, items):
        ''' items: list of item'''
        assert isinstance(items, list)
        item = items[0]
        fields = list(item.keys())
        values = [list(item.values()) for item in items]
        fieldstr = ','.join(fields)
        valstr = ','.join(['%s'] * len(item))
        sql = 'INSERT INTO {} ({}) VALUES({})'.format(
            table_name, fieldstr, valstr)
        cursor = self._cursor()
        try:
            last_id = cursor.executemany(sql, values)
            return last_id
        except Exception as e:
            print('\t', e)
            if e.args[0] == 1062:
                # just skip duplicated item error
                pass
            else:
                traceback.print_exc()
                print('sql:', sql)
                raise e

    def table_update(self, table_name, updates,
                     field_where, value_where):
        '''updates is a dict of {field_update:value_update}'''
        upsets = []
        values = []
        for k, v in updates.items():
            s = '{}=%s'.format(k)
            upsets.append(s)
            values.append(v)
        upsets = ','.join(upsets)
        sql = 'UPDATE {} SET {} WHERE {}="{}"'.format(
            table_name,
            upsets,
            field_where, value_where,
        )
        self.execute(sql, *(values))


if __name__ == "__main__":
    from pprint import pprint
    host = 'localhost'
    database = 'testdb'
    user = 'SYSDBA'
    password = 'SYSDBA001'
    db = ConnectionDM(
        host, database, 
        user, password,
        port=30236,
    )
    sql = 'select table_name from user_tables; '
    sql = 'select table_name from all_tables; '
    data = db.query(sql)
    pprint(data)
    db.close()
    
