import sys, json
import handle

# def get_data(request):
#     '''`request` here is really just any object that contains the JSON doc which
#     is the input to our handle function. In this example, we assume the request
#     is a JSON file on our local file system with a single line of JSON string.
#     But in a real system such as Lambda, the request could be an HTTP request,
#     and get_data() would unpack the HTTP request and pass the body to the handle
#     function.
#     '''
#     with open(request) as f:
#         data = f.read()
#         return data

def get_data():
    data = sys.stdin.read()

    return data

def main():
    data = get_data()
    ret = handle.handle(json.loads(data))
    ret = json.dumps(ret)

    print(ret)
    # TODO: simple return ret now. Might need to automatically store persistently
    return ret

if __name__ == "__main__":
    main()
