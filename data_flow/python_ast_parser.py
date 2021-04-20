import argparse
from data_flow import UnumPyAstProcessor


def main():
	parser = argparse.ArgumentParser(description='unum compiler')
	parser.add_argument('workflow')
	parser.add_argument("-a", "--ast", help="Dump the Python AST to stdout",
                    action="store_true")
	parser.add_argument("-d", "--data_flow", help="Print data flow to stdout",
                    action="store_true")
	args = parser.parse_args()

	with open(args.workflow) as wf:
		wf_source = wf.read()

	ast_parser = UnumPyAstProcessor()
	ast_parser.load(wf_source)

	if args.ast:
		ast_parser.dump_ast()

	ast_parser.build_dataflow()

	if args.data_flow:
		ast_parser.print_dag()


if __name__ == '__main__':
	main()
