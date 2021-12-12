"""A lightweight wrapper around PyMySQL for easy to use
Only for python 3
"""

import time
import traceback
import pymysql
import pymysql.cursors


class ConnectionSync:
    def __init__(self, host, database, user, password,
                 port=0,
                 max_idle_time=7*3600,
                 connect_timeout=10,
                 autocommit=True,
                 return_dict=True,
                 charset="utf8mb4"):
        self.max_idle_time = max_idle_time
        self._db_args = {
            'host': host,
            'database': database,
            'user': user,
            'password': password,
            'charset': charset,
            'autocommit': autocommit,
            'connect_timeout': connect_timeout,
        }
        if return_dict:
            self._db_args['cursorclass'] = pymysql.cursors.DictCursor
        if port:
            self._db_args['port'] = port
        self._db = None
        self._last_use_time = time.time()
        self.reconnect()

    def _ensure_connected(self):
        # Mysql by default closes client connections that are idle for
        # 8 hours, but the client library does not report this fact until
        # you try to perform a query and it fails.  Protect against this
        # case by preemptively closing and reopening the connection
        # if it has been idle for too long (7 hours by default).
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
            if not self._db_args['autocommit']:
                self._db.commit()
            self._db.close()
            self._db = None

    def reconnect(self):
        """Closes the existing database connection and re-opens it."""
        self.close()
        self._db = pymysql.connect(**self._db_args)

    def query_many(self, queries):
        """query many SQLs, Returns all result."""
        assert isinstance(queries, list)
        cursor = self._cursor()
        results = []
        for query in queries:
            try:
                cursor.execute(query)
                result = cursor.fetchall()
            except Exception as e:
                print(e)
                result = []
            results.append(result)
        return results

    def query(self, query, *parameters, **kwparameters):
        """Returns a row list for the given query and parameters."""
        cursor = self._cursor()
        try:
            cursor.execute(query, kwparameters or parameters)
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
            return cursor.fetchone()
        finally:
            cursor.close()

    def execute(self, query, *parameters, **kwparameters):
        """Executes the given query, returning the lastrowid from the query."""
        cursor = self._cursor()
        try:
            cursor.execute(query, kwparameters or parameters)
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
