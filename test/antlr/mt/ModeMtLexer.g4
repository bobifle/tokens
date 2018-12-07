lexer grammar ModeMtLexer;

GOOD_COMMENT
	: '//' ~[\r\n]* -> skip
;
HTML_COMMENT
	: '<!--' .*? '-->' -> skip
	;
OPEN
	: '[' -> pushMode(MT)
	;
CB
	: '}' ->popMode
	;
TEXT
	: ~('['|'}')+?
	;

mode MT ;

ADD: '+';
MUL: '*';
DIV: '/';
SUB: '-';
IF: 'if';
COUNT: 'count';
SEMI_COLON: ';';
COLON: ':';
COMMA: ',';
OP: '(';
CP: ')';
OB: '{' -> pushMode(DEFAULT_MODE);
ROLL: [1-9]* [0-9] [dD] [1-9]* [0-9]+;
NAME: [a-zA-Z_.] [a-zA-Z0-9_.]* ;
EQUAL : '=';
COMP_OP : ('==' | '<' | '>');
NUMBER : [0-9]+;
STRING : ( '\''     ('\\' (([ \t]+ ('\r'? '\n')?)|.) | ~[\\\r\n'])*  '\''
		| '"'      ('\\' (([ \t]+ ('\r'? '\n')?)|.) | ~[\\\r\n"])*  '"'
		)
		;
WS : [ \t\r\n]+ -> skip ; // skip spaces, tabs, newlines
CLOSE: ']' -> popMode ;
UNKNOWN: . ;
