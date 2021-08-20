"""A lightweight wrapper around aiomysql.Pool for easy to use
Only for Python 3
"""

import asyncio
import traceback
import aiomysql
import pymysql


class ConnectionAsync:
    def __init__(self, host, database, user, password,
                 loop=None,
                 minsize=3, maxsize=5,
                 return_dict=True,
                 pool_recycle=7*3600,
                 autocommit=True,
                 charset="utf8mb4",
                 **kwargs):
        '''
        kwargs: all parameters that aiomysql.connect() accept.
        '''
        self.db_args = {
            'host': host,
            'db': database,
            'user': user,
            'password': password,
            'minsize': minsize,
            'maxsize': maxsize,
            'charset': charset,
            'loop': loop,
            'autocommit': autocommit,
            'pool_recycle': pool_recycle,
        }
        if return_dict:
            self.db_args['cursorclass'] = aiomysql.cursors.DictCursor
        if kwargs:
            self.db_args.update(kwargs)
        self.pool = None

    def __del__(self):
        self.close()

    def close(self):
        if self.pool is not None:
            self.pool.terminate()
            self.pool = None

    async def select_db(self, db):
        await aiomysql.select_db(db)

    async def init_pool(self):
        if not self.db_args['loop']:
            self.db_args['loop'] = asyncio.get_running_loop()
        self.pool = await aiomysql.create_pool(**self.db_args)

    async def query_many(self, queries):
        """query many SQLs, Returns all result."""
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                results = []
                for query in queries:
                    try:
                        await cur.execute(query)
                        ret = await cur.fetchall()
                    except pymysql.err.InternalError:
                        await conn.ping()
                        await cur.execute(query)
                        ret = await cur.fetchall()
                    results.append(ret)
                return results

    async def query(self, query, *parameters, **kwparameters):
        """Returns a row list for the given query and parameters."""
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, kwparameters or parameters)
                    ret = await cur.fetchall()
                except pymysql.err.InternalError:
                    await conn.ping()
                    await cur.execute(query, kwparameters or parameters)
                    ret = await cur.fetchall()
                return ret

    async def get(self, query, *parameters, **kwparameters):
        """Returns the (singular) row returned by the given query.
        """
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, kwparameters or parameters)
                    ret = await cur.fetchone()
                except pymysql.err.InternalError:
                    await conn.ping()
                    await cur.execute(query, kwparameters or parameters)
                    ret = await cur.fetchone()
                return ret

    async def execute(self, query, *parameters, **kwparameters):
        """Executes the given query, returning the lastrowid from the query."""
        if not self.pool:
            await self.init_pool()
        async with self.pool.acquire() as conn:
            async with conn.cursor() as cur:
                try:
                    await cur.execute(query, kwparameters or parameters)
                except Exception:
                    # https://github.com/aio-libs/aiomysql/issues/340
                    await conn.ping()
                    await cur.execute(query, kwparameters or parameters)
                return cur.lastrowid

    # =============== high level method for table ===================

    async def table_has(self, table_name, field, value):
        sql = 'SELECT {} FROM {} WHERE {}=%s limit 1'.format(
            field, table_name, field)
        d = await self.get(sql, value)
        return d

    async def table_insert(self, table_name, item, ignore_duplicated=True):
        '''item is a dict : key is mysql table field'''
        fields = list(item.keys())
        values = list(item.values())
        fieldstr = ','.join(fields)
        valstr = ','.join(['%s'] * len(item))
        sql = 'INSERT INTO {} ({}) VALUES({})'.format(
            table_name, fieldstr, valstr)
        try:
            last_id = await self.execute(sql, *values)
            return last_id
        except Exception as e:
            if ignore_duplicated and e.args[0] == 1062:
                # just skip duplicated item
                return 0
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

    async def table_update(self, table_name, updates,
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
        await self.execute(sql, *(values))
