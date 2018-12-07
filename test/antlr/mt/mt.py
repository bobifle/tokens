import sys
import ast
import antlr4 as a4
import re
from ModeMtLexer import ModeMtLexer
from ModeMtParser import ModeMtParser
from ModeMtParserVisitor import ModeMtParserVisitor

class ParseError(Exception): pass

def listAppend(*args): return args

class MtVisitor(ModeMtParserVisitor):
	def __init__(self, *args, **kwargs):
		ModeMtParserVisitor.__init__(self, *args, **kwargs)
		self.memory = {'arg': (lambda a: "p%s"%a), 'listAppend': listAppend, 'roll': (lambda n, d: '%sd%s'%(n,d)), 'eval': lambda x:x, 'strformat': lambda x:x}
		self.out = ""
	def _visitAll(self, ctxlist):
		out = ""
		for c in ctxlist:
			ret = self.visit(c)
			if ret is not None: out += str(ret)
		return out
	def visitMtfile(self, ctx):
		self.output = self._visitAll(ctx.children)
	def visitHtml(self, ctx):
		return ctx.TEXT().getText()
	def visitBlock(self, ctx):
		print "Visiting a MT block %s, children: %s" % (ctx.getText(), [c.getText() for c in ctx.children])
		ro = ctx.NAME().getText() if ctx.NAME() else ""
		out = self._visitAll(ctx.children)
		return out if 'h' != ro else ''

	def visitIf_option(self, ctx):
		# note in the parent ctx we may fetch the display option
		test = eval(str(self.visit(ctx.test())))
		if (test): return self.visit(ctx.stat_expr(0))
		if (not test): return self.visit(ctx.stat_expr(1))
	def visitTest(self, ctx):
		if len(ctx.children) > 1: raise ParseError("Invalid test %s " % ctx.getText())
		foo =  self.visit(ctx.children[0])
		return foo
	def visitComparison(self, ctx):
		evalMe = "%s %s %s" % (self.visit(ctx.expr(0)), ctx.COMP_OP().getText(), self.visit(ctx.expr(1)))
		ret = eval(evalMe)
		return ret
	def visitExpr(self, ctx):
		if ctx.NUMBER() is not None: return self.visitNumber(ctx.NUMBER())
		if ctx.NAME() is not None: return self.visitName(ctx.NAME())
		if ctx.STRING() is not None: return self.visitString(ctx.STRING())
		if ctx.ADD() is not None: return self.visit(ctx.expr(0)) + self.visit(ctx.expr(1))
		if ctx.MUL() is not None: return self.visit(ctx.expr(0)) * self.visit(ctx.expr(1))
		if ctx.DIV() is not None: return self.visit(ctx.expr(0)) / self.visit(ctx.expr(1))
		if ctx.SUB() is not None: return self.visit(ctx.expr(0)) - self.visit(ctx.expr(1))
		if ctx.ROLL() is not None: return "rolling dice with %s" % ctx.ROLL().getText()
		if ctx.call() is not None:
			funcname = ctx.call().NAME().getText()
			func = self.memory.get(funcname, None)
			if func is None: raise ParseError('Unknown function <%s>' % funcname)
			return apply(func, [self.visit(e) for e in ctx.call().exprlist().expr()])
		# ( expr )
		if len(ctx.expr()) == 1 : return self.visit(ctx.expr(0))
		raise ParseError("Unkown expression type %s" % ctx.getText())
	def visitString(self, ctx):
		payload = re.sub(r'%{(.*?)}', r'%(\1)s', ctx.getText())
		payload = payload % self.memory
		return payload
	def visitNumber(self, ctx):
		return ast.literal_eval(ctx.getText())
	def visitName(self, ctx):
		name = ctx.getText()
		if name not in self.memory:
			raise ParseError("unkown symbol '%s'" % name)
		return self.memory[name]
	def visitAssign(self, ctx):
		name = ctx.NAME().getText()
		self.memory[name] = self.visit(ctx.expr())
		return self.memory[name]

def main(argv):
	input = a4.FileStream(argv[1])
	lexer = ModeMtLexer(input)
	stream = a4.CommonTokenStream(lexer)
	parser = ModeMtParser(stream)
	tree = parser.mtfile()
	visitor = MtVisitor()
	print "*** Lexxing and parsing the code ***"
	visitor.visit(tree)
	print "\n*** Memory state at the end of the macro: %s "% visitor.memory
	print "\n*** macro output:"
	print visitor.output
	return tree


if __name__ == '__main__':
   tree =  main(sys.argv)
