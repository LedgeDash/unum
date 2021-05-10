from mapreduce import emitPerReducerSingle, emitPerReducerBuffer

def user_map(event):
    text = event

    words = text.split()

    for word in words:
        emitPerReducerSingle(word)

    return
