import ast
from astpretty import pprint

class UnumDataflowNode(object):

	def __init__(self,name):
		self.flow_to=[]
		self.depends_on=[]
		self.name = name

class UnumDataflowDataNode(UnumDataflowNode):

	def __init__(self, name):
		super().__init__(name)

class UnumDataflowCallNode(UnumDataflowNode):
	def __init__(self, name):
		self.faas=False
		super().__init__(name)

	def set_faas():
		self.faas=True

class UnumPyAstProcessor(ast.NodeVisitor):
	'''Transform a Python ast to a data flow dag.

	Input to this processor is a single .py file of a FaaS function.
	'''

	def __init__(self):
		self.platform = 'aws'
		self.unum_faas_functions=[]
		self.local_functions=[]
		self.workflow_inputs=[]
		self.data_flow_dag=[]

	def load(self, source):
		self.ast_raw = ast.parse(source)

	def dump_ast(self):
		pprint(self.ast_raw)

	def print_dag(self):
		for n in self.workflow_inputs:
			self.print_node(n, 0)

	def print_node(self, n, indent):
		for i in range(0,indent):
			print('   ',end='')
		if indent > 0:
			print('|--->',end='')
		print(n.name)

		for ft in n.flow_to:
			self.print_node(ft,indent+1)

	def build_dataflow(self):
		self.visit(self.ast_raw)

	def visit_ImportFrom(self, node):
		if node.module == 'my_faas_functions':
			for f in node.names:
				self.unum_faas_functions.append(f.name)

	def visit_FunctionDef(self, node):
		if node.name == 'lambda_handler':
			# workflow inputs
			for a in node.args.args:
				input_node=UnumDataflowDataNode(a.arg)
				self.workflow_inputs.append(input_node)
				self.data_flow_dag.append(input_node)

			# traverse the function body
			self.generic_visit(node)

	def visit_Assign(self, node):


		# Left-hand side of an Assign
		# targets in Assign assumed to be a single Name object.
		if len(node.targets) == 1:
			if isinstance(node.targets[0], ast.Name):
				# TODO: overwrite variables with the same name
				target_node = UnumDataflowDataNode(node.targets[0].id)
				self.data_flow_dag.append(target_node)

			elif isinstance(node.targets[0], ast.Subscript):
				pass
		else:
			print("Assign targets has more than 1 element")

		# Right-hand side of an Assign
		source_node = self.visit(node.value)
		target_node.depends_on.append(source_node)
		source_node.flow_to.append(target_node)

		# # Right-hand side of an Assign
		# if isinstance(node.value, ast.Call):
		# 	# Handle when the same function (FaaS or local) is called multiple
		# 	# times by creating a UnumDataflowFaaSCallNode or
		# 	# UnumDataflowLocalCallNode everytime an ast.Call object is
		# 	# encountered.
		# 	call_obj = node.value
		# 	func_name = call_obj.func.id

		# 	call_node = UnumDataflowCallNode(func_name)

		# 	if func_name in unum_faas_functions:
		# 		call_node.set_faas()

		# 	# Look up and update input data nodes
		# 	for a in call_obj.args:
		# 		if isinstance(a, ast.Name):
		# 			# TODO: data node with the same name.
		# 			#
		# 			# If the arg is an ast.Name object, then there should
		# 			# exist an corresponding node in the self.data_flow_dag
		# 			input_data_node = self.find_node_by_name(a.id)
		# 			input_data_node.flow_to.append(call_node)
		# 			call_node.depends_on.append(input_data_node)

		# 		else:
		# 			print("call object args include unknown ast objects")
		# else:
		# 	print("unknown object on the right-hand side of assign")

	def visit_Call(self, node):
		call_node = UnumDataflowCallNode(node.func.id)
		args_node = [self.visit(a) for a in node.args]

		# update dependency
		for an in args_node:
			an.flow_to.append(call_node)
			call_node.depends_on.append(an)

		return call_node


	def visit_Name(self, node):
		# If it's a Name object, it should already be defined.
		n = self.find_node_by_name(node.id)
		if n == None:
			print("couldn't find data node with name: {}".format(node.id))

		return n

	def visit_Return(self,node):
		pass
		# print(node.value)

	def find_node_by_name(self, name):
		for n in self.data_flow_dag:
			if n.name == name:
				return n

		return None
