"""
Django 3 + Oracle 10g : le backend officiel utilise IDENTITY (12c+) et
user_tab_identity_cols (12c+). Ce module re applique le comportement
sequences + triggers et des types NUMBER sans IDENTITY.

A appeler depuis settings une fois, avant toute connexion a la base.
"""
from django.db import models
from django.db.backends.utils import strip_quotes, truncate_name


_SEQUENCE_RESET_SQL_10G = """
DECLARE
    table_value integer;
    seq_value integer;
BEGIN
    SELECT NVL(MAX(%(column)s), 0) INTO table_value FROM %(table)s;
    SELECT NVL(last_number - cache_size, 0) INTO seq_value FROM user_sequences
           WHERE sequence_name = '%(no_autofield_sequence_name)s';
    WHILE table_value > seq_value LOOP
        SELECT "%(no_autofield_sequence_name)s".nextval INTO seq_value FROM dual;
    END LOOP;
END;
/"""


def _autoinc_sql(self, table, column):
    sq_name = self._get_no_autofield_sequence_name(table)
    name_length = self.max_name_length() - 3
    tr_name = "%s_TR" % truncate_name(strip_quotes(table), name_length).upper()
    args = {
        "sq_name": sq_name,
        "tr_name": tr_name,
        "tbl_name": self.quote_name(table),
        "col_name": self.quote_name(column),
    }
    sequence_sql = """
DECLARE
    i INTEGER;
BEGIN
    SELECT COUNT(1) INTO i FROM USER_SEQUENCES
        WHERE SEQUENCE_NAME = '%(sq_name)s';
    IF i = 0 THEN
        EXECUTE IMMEDIATE 'CREATE SEQUENCE "%(sq_name)s"';
    END IF;
END;
/""" % args
    trigger_sql = """
CREATE OR REPLACE TRIGGER "%(tr_name)s"
    BEFORE INSERT ON %(tbl_name)s
    FOR EACH ROW
    WHEN (new.%(col_name)s IS NULL)
BEGIN
    SELECT "%(sq_name)s".nextval INTO :new.%(col_name)s FROM dual;
END;
/""" % args
    return sequence_sql, trigger_sql


def _get_sequence_name_10g(self, cursor, table, pk_name):
    return self._get_no_autofield_sequence_name(table)


def _last_insert_id_10g(self, cursor, table_name, pk_name):
    sq = self._get_no_autofield_sequence_name(strip_quotes(table_name))
    cursor.execute('SELECT "%s".currval FROM dual' % sq)
    return cursor.fetchone()[0]


def _is_identity_column_false(self, table_name, column_name):
    return False


def _cache_key_culling_sql_10g(self):
    return (
        "SELECT cache_key FROM (SELECT cache_key, "
        "rank() OVER (ORDER BY cache_key) AS rnk FROM %s) WHERE rnk = %%s + 1"
    )


def _get_sequences_10g(self, cursor, table_name, table_fields=()):
    for f in table_fields:
        if isinstance(f, models.AutoField):
            return [{"table": table_name, "column": f.column}]
    return []


def _get_table_description_10g(self, cursor, table_name):
    from django.db.backends.oracle.introspection import FieldInfo

    cursor.execute(
        """
            SELECT
                column_name,
                data_default,
                CASE
                    WHEN char_used IS NULL THEN data_length
                    ELSE char_length
                END AS internal_size,
                0 AS is_autofield
            FROM user_tab_cols
            WHERE table_name = UPPER(%s)
        """,
        [table_name],
    )
    field_map = {
        column: (internal_size, default if default != "NULL" else None, is_autofield)
        for column, default, internal_size, is_autofield in cursor.fetchall()
    }
    self.cache_bust_counter += 1
    cursor.execute(
        "SELECT * FROM {} WHERE ROWNUM < 2 AND {} > 0".format(
            self.connection.ops.quote_name(table_name),
            self.cache_bust_counter,
        )
    )
    description = []
    for desc in cursor.description:
        name = desc[0]
        internal_size, default, is_autofield = field_map[name]
        name = name % {}
        description.append(
            FieldInfo(
                self.identifier_converter(name),
                *desc[1:3],
                internal_size,
                desc[4] or 0,
                desc[5] or 0,
                *desc[6:],
                default,
                is_autofield,
            )
        )
    return description


def apply_patches():
    from django.db.backends.oracle import base as oracle_base
    from django.db.backends.oracle import introspection as oracle_introspection
    from django.db.backends.oracle import operations as oracle_ops
    from django.db.backends.oracle import schema as oracle_schema

    dt = dict(oracle_base.DatabaseWrapper.data_types)
    dt["AutoField"] = "NUMBER(11)"
    dt["BigAutoField"] = "NUMBER(19)"
    dt["SmallAutoField"] = "NUMBER(5)"
    oracle_base.DatabaseWrapper.data_types = dt

    Ops = oracle_ops.DatabaseOperations
    Ops._sequence_reset_sql = _SEQUENCE_RESET_SQL_10G
    Ops.autoinc_sql = _autoinc_sql
    Ops._get_sequence_name = _get_sequence_name_10g
    Ops.last_insert_id = _last_insert_id_10g
    Ops.cache_key_culling_sql = _cache_key_culling_sql_10g
    Ops.compiler_module = "projet_oracle.oracle10g_compiler"

    oracle_schema.DatabaseSchemaEditor._is_identity_column = _is_identity_column_false
    oracle_introspection.DatabaseIntrospection.get_sequences = _get_sequences_10g
    oracle_introspection.DatabaseIntrospection.get_table_description = (
        _get_table_description_10g
    )
