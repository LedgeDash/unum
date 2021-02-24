import sys,json

operator = sys.stdin.read()
operator = json.loads(operator)

# create environment
for k in operator:
	if k != 'code':
		env_str = '''{} = {}'''.format(k, operator[k])
		exec(env_str)
# execute code
exec(operator['code'])
# print(operator)
print(unum_ret)