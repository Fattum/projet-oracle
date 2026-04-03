"""
LIMIT/OFFSET pour Oracle < 12c : ROWNUM au lieu de OFFSET ... FETCH FIRST.
"""
from django.db.models.sql import compiler


class SQLCompiler(compiler.SQLCompiler):
    def as_sql(self, with_limits=True, with_col_aliases=False):
        do_offset = with_limits and (
            self.query.high_mark is not None or self.query.low_mark
        )
        if not do_offset:
            return super().as_sql(
                with_limits=with_limits, with_col_aliases=with_col_aliases
            )
        sql, params = super().as_sql(with_limits=False, with_col_aliases=True)
        high_where = ""
        if self.query.high_mark is not None:
            high_where = "WHERE ROWNUM <= %d" % (self.query.high_mark,)
        if self.query.low_mark:
            sql = (
                'SELECT * FROM (SELECT "_SUB".*, ROWNUM AS "_RN" FROM (%s) '
                '"_SUB" %s) WHERE "_RN" > %d'
                % (sql, high_where, self.query.low_mark)
            )
        else:
            sql = 'SELECT * FROM (SELECT "_SUB".* FROM (%s) "_SUB" %s)' % (
                sql,
                high_where,
            )
        return sql, params


class SQLInsertCompiler(compiler.SQLInsertCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler):
    pass


class SQLUpdateCompiler(compiler.SQLUpdateCompiler):
    pass


class SQLAggregateCompiler(compiler.SQLAggregateCompiler):
    pass
