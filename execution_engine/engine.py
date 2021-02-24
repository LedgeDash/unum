# recv HTTP request
# get payload
# get application name
# get application IR

# individual invoke.py: 
#     execute operator
#     execute faas function handle
#     execute operator

# Read from stdin a JSON string of the format:
# {"app": string, "data": object}
# check if app.unum exists.
# Execute the app

import sys, json
import os.path
from subprocess import Popen, PIPE, STDOUT


class BaseNode(object):
	"""docstring for ClassName"""
	def __init__(self, name, arg):
		self.name = name
		self.raw = arg
		self.type = arg['type']
		self.ready = False

		self.dep = []
		self.complete = False
		self.leaf = False

	def __str__(self):
		return "name: " + self.name + "\n" + 'type: ' + self.type + '\n' + "depends on: " + str(self.dep)+ '\n'+ 'ready: ' + str(self.ready) + '\n'+ 'complete: ' + str(self.complete) + '\n'

	def __repr__(self):
		return self.name + ', ' + str(self.__class__)

	def depends_on(self, dep):
		self.dep.append(dep)

	def complete(self):
		self.complete = True

	def check_ready(self):
		if self.ready == True:
			return True

		for d in self.dep:
			if d.complete == False:
				return False

		return True


class InputNode(BaseNode):
	"""docstring for FunctionNode"""
	def __init__(self, name, arg):
		super().__init__(name,arg)

	def __repr__(self):
		return self.name + ', ' + str(self.__class__)

	def populate_data(self, input_data):
		self.data = input_data
		self.ready = True

	def run(self):
		self.result = self.data
		super().complete()

class FunctionNode(BaseNode):
	"""docstring for FunctionNode"""
	def __init__(self, name, arg):
		super().__init__(name,arg)
		self.location = arg['location']
		os.path.isfile(self.location+"handle.py")
		os.path.isfile(self.location+"invoke.py")

		self.args = arg['args']

	def __repr__(self):
		return self.name + ', ' + str(self.__class__)

	def run(self):
		'''Current limitation: only a single input
		'''
		input_data = [d.result for d in self.dep][0]
		prog = self.location+'invoke.py'

		# input_data = json.loads(input_data)
		# payload = {}
		# payload['data'] = input_data
		# payload = json.dumps(payload)

		with Popen(['python3', prog], stdout = PIPE, stdin=PIPE, stderr=PIPE) as proc:
			try:
			    outs, errs = proc.communicate(input=bytes(input_data,encoding='utf-8'),timeout=15)
			except TimeoutExpired:
			    proc.kill()
			    outs, errs = proc.communicate()

		ret = outs.decode('utf-8').replace("'", '"') #subprocess-specific: subprocess returns bytes
		self.result = ret
		# print('FaaS function name: ' + self.name)
		# print('Result: '+ self.result)
		# print('Result type: ' + str(type(self.result)))
		# print('Errors: ' + str(errs))
		# print('\n')
		super().complete()


class OperatorNode(BaseNode):
	"""docstring for FunctionNode"""
	def __init__(self, name, arg):
		super().__init__(name,arg)
		self.code = arg['code']
		self.args = arg['args']

	def __repr__(self):
		return self.name + ', ' + str(self.__class__)

	def run(self):

		states = {}
		states['code'] = self.code
		for var_name, var_value in zip(self.args, self.dep):
			states[var_name] = var_value.result

		states_json = json.dumps(states)

		with Popen(['python3', 'operator.py'], stdout=PIPE, stdin=PIPE, stderr=PIPE) as proc:
			try:
			    outs, errs = proc.communicate(input=bytes(states_json,encoding='utf-8'),timeout=15)
			except TimeoutExpired:
			    proc.kill()
			    outs, errs = proc.communicate()

		# ret = subprocess.run(['python3', 'operator.py'], capture_output=True)
		ret = outs.decode('utf-8').replace("'", '"') #subprocess-specific: subprocess returns bytes
		self.result = ret
		# print('Operator name: ' + self.name)
		# print('Result: '+ self.result)
		# print('Result type: ' + str(type(self.result)))
		# print('Errors: ' + str(errs))
		# print('\n')
		super().complete()

def find_node_by_name(ir, name):
	for n in ir:
		if n.name == name:
			return n

	return None

def build_dependency(ir):
	for n in ir:
		if n.type != 'input':
			for dn in n.args:
				d = find_node_by_name(ir, dn)
				n.depends_on(d)


def update_readiness(ir):
	for n in ir:
		if n.check_ready():
			n.ready = True

def check_complete(ir):
	for n in ir:
		if n.complete == False:
			return False
	return True

def setup_input(ir, input_data):
	''' Current limitation: only one input node per app is allowed.
	'''
	num = 0
	for n in ir:
		if n.type == 'input':
			n.populate_data(input_data)
			num = num+1

	if num!=1:
		raise

def execute_app(ir, input_data):

	setup_input(ir, input_data)

	while check_complete(ir) == False:
		for n in ir:
			if n.complete == False and n.ready == True:
				n.run() # TODO: can use a ready queue to parallelize
		update_readiness(ir)

def check_leaf(node, ir):
	for n in ir:
		if node in n.dep:
			return False
	return True

def mark_leaf_nodes(ir):
	for n in ir:
		if check_leaf(n, ir):
			n.leaf = True

def get_result(ir):
	ret = []
	for n in ir:
		if n.leaf:
			ret.append(n.result)
	return ret

def main():
	for line in sys.stdin:
		req = json.loads(line)
		ir_filename = req['app']+'.unum'
		input_data = json.dumps(req['data'])

		# IR is just a list of Node objects
		with open(ir_filename, 'r') as f:
			ir_raw = json.loads(f.read())
			ir = []
			for k in ir_raw:
				if ir_raw[k]['type'] == 'function':
					n = FunctionNode(k, ir_raw[k])
				elif ir_raw[k]['type'] == 'operator':
					n = OperatorNode(k, ir_raw[k])
				elif ir_raw[k]['type'] == 'input':
					n = InputNode(k, ir_raw[k])
				else:
					n = BaseNode(k, ir_raw[k])
				ir.append(n)

		build_dependency(ir)
		mark_leaf_nodes(ir)

		execute_app(ir, input_data)

		ret = get_result(ir)
		print(ret)

if __name__ == "__main__":
	main()