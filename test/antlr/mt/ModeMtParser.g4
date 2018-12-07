parser grammar ModeMtParser;

options {tokenVocab=ModeMtLexer;}

// default mode is raw html

entry: mtfile;
// a MT file is a collection of MT blocks or html
mtfile: (('[' block ']') | html)*;

// a MT block embbed MT code
block: stat_expr | (NAME ':' stat_expr) | ((NAME ',')? (if_option | count_option));

// statement or expression
stat_expr: assign | expr;

assign : NAME EQUAL expr ;
if_option : 'if' '(' test ')' ':' stat_expr ';' stat_expr;
count_option : 'count' '(' expr ')' ':' stat_expr ;
test: (expr | comparison);
comparison: expr COMP_OP expr;
expr:
	expr ( MUL|DIV) expr
	| expr (ADD|SUB) expr
	| call
	| ROLL | NUMBER | NAME | STRING
	| '(' expr ')';
exprlist: expr (',' expr)* ','?;
call: NAME '(' exprlist? ')';

html: TEXT ;
