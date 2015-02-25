# dbmap
Database mapping tool. Builds relational diagram of RDBMS tables.
 * Works with ANSI infromation_schema tables, thus compatible with different database engines. Tested with MS SQL and PostgreSQL.
 * Runs in python 2.x or 3.x
 * Produces GraphViz text files. Those could be exported to PDF or image files. 

##Dependencies
 * FreeTDS
 * pymssql
 * sqlalchemy

##Automatically Generated Usage Message
usage: dbmap.py [-h] [-p PASSWORD] [-f OUTPUT_FILE_NAME] [-s SCHEMAS]
                [-t TABLES] [-n]
                database_type host_name database_name login_name

Build a relationship diagram of a RDMS database. Produces GraphViz file (.gv).
You can open it with GraphVis to view the actual diagram.

positional arguments:
  database_type         Database engine type in SQL Alchemy. You can google
                        them with string like "sqlalchemy engine
                        configuration". Here is a URL with current version of
                        SQL Alchemy: http://docs.sqlalchemy.org/en/rel_0_9/cor
                        e/engines.html. EXAMPLES: postgresql+psycopg2,
                        mssql+pymssql
  host_name             SQL Server host name
  database_name         Source database name
  login_name            Login name

optional arguments:
  -h, --help            show this help message and exit
  -p PASSWORD, --password PASSWORD
                        Password for the login_name
  -f OUTPUT_FILE_NAME, --file OUTPUT_FILE_NAME
                        If not provided, output will be printed to standard
                        output.
  -s SCHEMAS, --schemas SCHEMAS
                        Comma separated (no spaces) list of schemas to make
                        relationship diagram for. If not provided, all schemas
                        will be processed.
  -n, --names-only      User table names only, no column information will be
                        printed.
```

##Example:
```
python3 mssql2pg.py SqlServer PgConversionExample user1 p4ssw0rd -f example.sql -d conversion_example -u
python dbmap.py postgresql localhost db user -s wiki -f wiki.gv
```

##Output:
```
digraph database_schema {
    rankdir=RL;
    node [shape=plaintext]
    splines=compound

    Blog_Comments[label=<
<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0'>
    <tr><td colspan='2' bgcolor='lightgray'>Blog.Comments</td></tr>
    <tr><td port='CommentID' align='left'><font color='blue'>CommentID</font></td><td port='CommentID_to' align='left'>int</td></tr>
    <tr><td port='PostID' align='left'>PostID</td><td port='PostID_to' align='left'>int</td></tr>
    <tr><td port='Title' align='left'>Title</td><td port='Title_to' align='left'>nvarchar(300)</td></tr>
    <tr><td port='Content' align='left'>Content</td><td port='Content_to' align='left'>nvarchar(max)</td></tr>
    <tr><td port='AnonymousFlag' align='left'>AnonymousFlag</td><td port='AnonymousFlag_to' align='left'>bit</td></tr>
</TABLE>
    >];

    Blog_Posts[label=<
<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0'>
    <tr><td colspan='2' bgcolor='lightgray'>Blog.Posts</td></tr>
    <tr><td port='PostID' align='left'><font color='blue'>PostID</font></td><td port='PostID_to' align='left'>int</td></tr>
    <tr><td port='ModuleID' align='left'>ModuleID</td><td port='ModuleID_to' align='left'>int</td></tr>
    <tr><td port='Title' align='left'>Title</td><td port='Title_to' align='left'>nvarchar(300)</td></tr>
    <tr><td port='Content' align='left'>Content</td><td port='Content_to' align='left'>nvarchar(max)</td></tr>
    <tr><td port='Preview' align='left'>Preview</td><td port='Preview_to' align='left'><font color='#C7B097'>nvarchar(2000)</font></td></tr>
    <tr><td port='FriendlyUrl' align='left'>FriendlyUrl</td><td port='FriendlyUrl_to' align='left'>nvarchar(300)</td></tr>
</TABLE>
    >];

    Blog_Visits[label=<
<TABLE BORDER='0' CELLBORDER='1' CELLSPACING='0'>
    <tr><td colspan='2' bgcolor='lightgray'>Blog.Visits</td></tr>
    <tr><td port='ID' align='left'>ID</td><td port='ID_to' align='left'>int</td></tr>
    <tr><td port='PostID' align='left'>PostID</td><td port='PostID_to' align='left'>int</td></tr>
    <tr><td port='UserID' align='left'>UserID</td><td port='UserID_to' align='left'>int</td></tr>
    <tr><td port='VisitDateTime' align='left'>VisitDateTime</td><td port='VisitDateTime_to' align='left'>datetime</td></tr>
</TABLE>
    >];

    node [shape=recorder style=filled fillcolor=lightgray]

    Blog_Visits:PostID -> Blog_Posts:PostID_TO[arrowhead=normal arrowtail=tee dir=both]
    Blog_Comments:PostID -> Blog_Posts:PostID_TO[arrowhead=normal arrowtail=tee dir=both]
}
```