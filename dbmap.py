import argparse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import codecs
import getpass


class DbMap:
    def __init__(self):
        self.param_sql_session = None
        self.param_output_file = None
        self.param_schemas = None
        self.param_tables = None
        self.param_names_only = None
        self.param_first_relationships = None
        self.param_second_relationships = None

        self.schemas = None
        self.tables = None
        self.columns = None
        self.constraints_pk = None
        self.constraints_fk = None

        self.tables_to_print = None

    def read_command_line_params(self):
        parser = argparse.ArgumentParser(description='''
Build a relationship diagram of a RDMS database.
Produces GraphViz file (.gv). You can open it with GraphVis to view the actual diagram.
        ''')

        parser.add_argument('database_type',
                            help='''
Database engine type in SQL Alchemy.
You can google them with string like "sqlalchemy engine configuration".
Here is a URL with current version of SQL Alchemy:
http://docs.sqlalchemy.org/en/rel_0_9/core/engines.html.
EXAMPLES: postgresql+psycopg2, mssql+pymssql
                            ''')
        parser.add_argument('host_name', help='SQL Server host name')
        parser.add_argument('database_name', help='Source database name')
        parser.add_argument('login_name', help='Login name')

        parser.add_argument('-p', '--password', dest='password', help='Password for the login_name')

        parser.add_argument('-f', '--file', dest='output_file_name', default='',
                            help='If not provided, output will be printed to standard output.')

        parser.add_argument('-s', '--schemas', dest='schemas', default='',
                            help='''
Comma separated (no spaces) list of schemas to make relationship diagram for.
If not provided, all schemas will be processed.
                            ''')

        parser.add_argument('-t', '--tables', dest='tables', default='',
                            help='''
Comma separated (no spaces) list of table names ([<schema>.]<table>) to make relationship diagram for.
If provided, specified tables will be displayed.
                            ''')

        parser.add_argument('-1', '--first-relationships', dest='first_relationships', action='store_true', default=False,
                            help='If provided, first relationships of selected tables will also be displayed.')

        parser.add_argument('-2', '--second-relationships', dest='second_relationships', action='store_true', default=False,
                            help='If provided, first and second relationships of selected tables will also be displayed.')

        parser.add_argument('-n', '--names-only', action='store_true', default=False, dest='names_only',
                            help='User table names only, no column information will be printed.')

        ####################################################
        args = parser.parse_args()

        # if args.first_tables != '' and args.schemas != '':
        #     raise SystemExit('ERROR: Cannot use parameters -s/--schemas and -1/--first-relationships in combination')

        if args.password is None:
            args.password = getpass.getpass('Password:')

        connection_string = '{}://{}:{}@{}/{}'.format(
            args.database_type, args.login_name, args.password, args.host_name, args.database_name)
        engine = create_engine(connection_string)

        self.param_sql_session = sessionmaker(bind=engine, autocommit=True)()
        self.param_output_file = args.output_file_name

        if args.schemas != '':
            self.param_schemas = args.schemas.lower().split(',')
        else:
            self.param_schemas = []

        if args.tables != '':
            self.param_tables = args.tables.lower().split(',')
        else:
            self.param_tables = []

        self.param_first_relationships = args.first_relationships
        self.param_second_relationships = args.second_relationships
        self.param_names_only = args.names_only

    def run(self):
        self.read_command_line_params()

        if self.param_output_file is not None:
            try:
                file_name = self.param_output_file
                self.param_output_file = codecs.open(self.param_output_file, 'w', 'utf-8')
            except Exception as e:
                raise SystemExit('Error opening file {}: {}'.format(file_name, e))

        try:
            try:
                self.output_progress('reading tables')
                if len(self.param_tables) == 0:
                    self.tables = self.read_tables()
                else:
                    self.tables = self.read_tables()

                self.output_progress('reading columns')
                self.columns = self.read_columns()
                self.output_progress('reading primary keys')
                self.constraints_pk = self.read_constraints_pk()
                self.output_progress('reading foreign keys')
                self.constraints_fk = self.read_constraints_fk()

                self.tables_to_print = self.select_tables_for_output()

                self.output_progress('writing database')
                if not self.param_names_only:
                    self.output_graph_with_columns()
                else:
                    self.output_graph_names_only()

            finally:
                self.param_sql_session.close()
        finally:
            if self.param_output_file is not None:
                self.param_output_file.close()

    def write_string(self, s):
        if self.param_output_file is not None:
            self.param_output_file.write(s + '\n')
        else:
            print(s)

    def output_progress(self, comment):
        if self.param_output_file is not None:
            print(comment)

    def translate_column_type(self, column):
        column_type = column['type'].lower()

        result = column_type
        if column['char_length'] is not None:
            if column['char_length'] == -1:
                result += '(max)'
            else:
                result += '({})'.format(column['char_length'])
        elif column['precision'] is not None:
            if 'int' not in column_type:
                result += '({}, {})'.format(column['precision'], column['scale'])

        return result

    def translate_table_name(self, schema, table):
        if schema in ('dbo', 'public'):
            result = table
        else:
            result = '{}.{}'.format(schema, table)

        return result

    def read_tables(self):
        try:
            r = self.param_sql_session.execute("""
    SELECT table_schema, table_name
    FROM information_schema.tables
    WHERE table_type = 'BASE TABLE'
      AND table_name NOT IN ('dtproperties', 'sysdiagrams')
      AND table_schema NOT IN ('information_schema', 'pg_catalog')
    ORDER BY table_schema, table_name
            """)
        except Exception as e:
            raise SystemExit('Error connecting to database {}'.format(e.orig))

        result = []
        for row in r:
            table_name = self.translate_table_name(row["table_schema"], row["table_name"])
            result.append(table_name)

        return result

    def read_columns(self):
        r = self.param_sql_session.execute("""
SELECT table_schema,
  table_name,
  column_name,
  column_default,
  is_nullable,
  data_type,
  character_maximum_length,
  numeric_precision,
  numeric_scale
FROM INFORMATION_SCHEMA.COLUMNS
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION
        """)

        result = {}
        for row in r:
            table_name = self.translate_table_name(row["table_schema"], row["table_name"])

            table_column = dict(
                name=row['column_name'],
                type=row['data_type'],
                default=row['column_default'],
                nullable=row['is_nullable'],
                char_length=row['character_maximum_length'],
                precision=row['numeric_precision'],
                scale=row['numeric_scale'],
            )

            table_column['translated_type'] = self.translate_column_type(table_column)

            if table_name not in result:
                result[table_name] = []

            result[table_name].append(table_column)

        return result

    def read_constraints_pk(self):
        r = self.param_sql_session.execute("""
SELECT u.table_schema, u.table_name, u.column_name, c.constraint_type
FROM INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE u
INNER JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS c
  ON  c.CONSTRAINT_NAME = u.CONSTRAINT_NAME
  AND c.CONSTRAINT_SCHEMA = u.CONSTRAINT_SCHEMA
WHERE c.CONSTRAINT_TYPE IN ('PRIMARY KEY')
        """)

        result = {}
        for row in r:
            table_name = self.translate_table_name(row["table_schema"], row["table_name"])
            if table_name not in result:
                result[table_name] = []

            result[table_name].append(row['column_name'])

        return result

    def read_constraints_fk(self):
        r = self.param_sql_session.execute("""
SELECT kcu1.constraint_schema as constraint_schema,
  kcu1.constraint_name as constraint_name,
  kcu1.table_schema as table_schema,
  kcu1.table_name as table_name,
  kcu1.column_name as column_name,
  kcu1.ordinal_position as ordinal_position,
  kcu2.constraint_schema as unique_constraint_schema,
  kcu2.constraint_name as unique_constraint_name,
  kcu2.table_schema as unique_table_schema,
  kcu2.table_name as unique_table_name,
  kcu2.column_name as unique_column_name
FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS RC
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE KCU1
  ON  KCU1.CONSTRAINT_CATALOG = RC.CONSTRAINT_CATALOG
  AND KCU1.CONSTRAINT_SCHEMA = RC.CONSTRAINT_SCHEMA
  AND KCU1.CONSTRAINT_NAME = RC.CONSTRAINT_NAME
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE KCU2
  ON  KCU2.CONSTRAINT_CATALOG = RC.UNIQUE_CONSTRAINT_CATALOG
  AND KCU2.CONSTRAINT_SCHEMA = RC.UNIQUE_CONSTRAINT_SCHEMA
  AND KCU2.CONSTRAINT_NAME = RC.UNIQUE_CONSTRAINT_NAME
WHERE KCU1.ORDINAL_POSITION = KCU2.ORDINAL_POSITION
  AND KCU1.TABLE_SCHEMA not in ('sys', 'guest', 'information_schema')
ORDER BY CONSTRAINT_SCHEMA, CONSTRAINT_NAME
        """)

        result = []
        for row in r:
            table_name = self.translate_table_name(row["table_schema"], row["table_name"])
            pk_table_name = self.translate_table_name(row["unique_table_schema"], row["unique_table_name"])
            pk = {
                'table': table_name,
                'column': row['column_name'],
                'pk_table': pk_table_name,
                'pk_column': row['unique_column_name'],
            }
            result.append(pk)

        return result

    def select_dependent_tables(self, tables):
        result = []

        for table in tables:
            fks = [fk for fk in self.constraints_fk if fk['table'].lower() == table.lower()]
            for fk in fks:
                result.append(fk['pk_table'])

            fks = [fk for fk in self.constraints_fk if fk['pk_table'].lower() == table.lower()]
            for fk in fks:
                result.append(fk['table'])

        result = list(set(tables) | set(result))
        return result

    def select_tables_for_output(self):
        result = []

        if len(self.param_schemas) == 0 and len(self.param_tables) == 0:
            result = self.tables
        else:
            if len(self.param_schemas) > 0:
                for param_schema in self.param_schemas:
                    result = [table for table in self.tables if table.lower().startswith(param_schema+'.')]

            if len(self.param_tables) > 0:
                for param_table in self.param_tables:
                    result = [table for table in self.tables if table.lower() == param_table]

            if self.param_first_relationships or self.param_second_relationships:
                result = self.select_dependent_tables(result)

            if self.param_second_relationships:
                result = self.select_dependent_tables(result)

        result = list(set(result))
        print(result)

        return result

    def output_graph_with_columns(self):
        self.param_output_file.write("digraph database_schema {\n")
        self.param_output_file.write("    rankdir=RL;\n")
        self.param_output_file.write("    node [shape=plaintext]\n")
        self.param_output_file.write("    splines=compound\n\n")

        for table in self.tables_to_print:
            self.param_output_file.write("    {}[label=<\n".format(table.replace('.', '_')))
            self.param_output_file.write("<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0'>\n")
            self.param_output_file.write("    <tr><td colspan='2' bgcolor='lightgray'>{}</td></tr>\n".format(table))

            pk = None
            if self.constraints_pk is not None and table in self.constraints_pk:
                pk = self.constraints_pk[table]

            for column in self.columns[table]:
                column_name = column['name']
                if pk is not None and column['name'] in pk:
                    column_name = "<font color='blue'>{}</font>".format(column_name)

                column_type = column['translated_type']
                if column['nullable'] == 'YES':
                    column_type = "<font color='#C7B097'>{}</font>".format(column_type)

                self.param_output_file.write(
                    "    <tr><td port='{port}' align='left'>{name}</td>"
                    "<td port='{port}_to' align='left'>{type}</td></tr>\n".format(
                        port=column['name'].replace(".", "_"),
                        name=column_name,
                        type=column_type,
                    ),
                )

            self.param_output_file.write("</TABLE>\n")
            self.param_output_file.write("    >];\n\n")

        #references
        #Tables without fields should have shapes, not just text
        self.param_output_file.write("    node [shape=recorder style=filled fillcolor=lightgray]\n\n")
        for constraint in self.constraints_fk:
            if constraint['table'] in self.tables_to_print and constraint['pk_table'] in self.tables_to_print:
                from_name = "{}:{}".format(constraint['table'].replace('.', '_'), constraint['column'])
                to_name = "{}:{}_TO".format(constraint['pk_table'].replace('.', '_'), constraint['pk_column'])

                self.param_output_file.write(
                    "    {} -> {}[arrowhead=normal arrowtail=tee dir=both]\n".format(from_name, to_name)
                )

        self.param_output_file.write("}\n")

    def output_graph_names_only(self):
        self.param_output_file.write("digraph database_schema {\n")
        self.param_output_file.write("    rankdir=RL;\n")
        self.param_output_file.write("    node [shape=block]\n")
        self.param_output_file.write("    splines=compound\n\n")

        for table in self.tables_to_print:
            self.param_output_file.write('    {}[label="{}"]\n'.format(table.replace('.', '_'), table))

        #references
        #Tables without fields should have shapes, not just text
        self.param_output_file.write("    node [shape=recorder style=filled fillcolor=lightgray]\n\n")
        for constraint in self.constraints_fk:
            if constraint['table'] in self.tables_to_print and constraint['pk_table'] in self.tables_to_print:
                from_name = constraint['table'].replace('.', '_')
                to_name = constraint['pk_table'].replace('.', '_')

                self.param_output_file.write(
                    "    {} -> {}[arrowhead=normal arrowtail=tee dir=both]\n".format(from_name, to_name)
                )

        self.param_output_file.write("}\n")

diagram = DbMap()
diagram.run()
