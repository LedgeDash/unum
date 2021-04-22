import argparse
import os, json, sys
from data_flow.data_flow import UnumPyAstProcessor, UnumDataflowCallNode

def find_faas_function_config(name, config):
	for fc in config['faas_functions']:
		if fc['name'] == name:
			return fc
	return None

def compile(dag, workflow_config):
	for n in dag.workflow_inputs:
		compile_node(n, workflow_config)

def compile_node(node, workflow_config):
	for n in node.flow_to:
		compile_node(n, workflow_config)

	if isinstance(node,UnumDataflowCallNode) and node.faas==True:

		function_config=find_faas_function_config(node.name, workflow_config)

		if function_config == None:
			exit("FaaS function {} not found".format(node.name))

		if len(node.flow_to) > 0:
			func_dir = os.path.dirname(function_config['location'])
			path = os.path.join(sys.argv[1], func_dir)
			dest = open(os.path.join(path, ".destination"), "w")

			for n in node.flow_to:
				dest.write(str(n.name))


def add_dest(node):
	pass

def main():
	parser = argparse.ArgumentParser(description='unum compiler')
	parser.add_argument('workflow')
	parser.add_argument("-a", "--ast", help="Dump the Python AST to stdout",
                    action="store_true")
	parser.add_argument("-d", "--data_flow", help="Print data flow to stdout",
                    action="store_true")
	parser.add_argument("-c", "--compile", help="Compile into deployable packages",
                    action="store_true")
	args = parser.parse_args()

	entries = os.listdir(args.workflow)

	if "config.json" not in entries:
		exit(1)

	with open(os.path.join(args.workflow, "config.json")) as c:
		workflow_config = json.loads(c.read())

	#print(workflow_config)


	# workflow analysis
	with open(os.path.join(args.workflow, workflow_config['workflow'])) as wf:
		wf_source = wf.read()

	ast_parser = UnumPyAstProcessor()
	ast_parser.load(wf_source)

	if args.ast:
		ast_parser.dump_ast()

	ast_parser.build_dataflow()

	if args.data_flow:
		ast_parser.print_dag()
	
	if args.compile:
		compile(ast_parser, workflow_config)

if __name__ == '__main__':
	main()