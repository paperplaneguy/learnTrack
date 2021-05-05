from sys          import argv
from socket       import create_connection, gethostbyname
from textwrap     import dedent
from pprint       import pprint
from urllib.parse import quote_plus
from pymongo      import MongoClient

import constants as consts

argc = len(argv)
db = MongoClient(
    'mongodb://' + consts.username + ':' + quote_plus(consts.password) + '@' + consts.address + ':' + consts.port +
    '/learnTrack'
).learnTrack.personal
maxitems = 30
version = "0.5.3"

def _print(c):
    print(c, end="")
def db_len():
    return db.estimated_document_count()
def decrement(entity_name):
    count = get_entity_count(entity_name)
    if count > 0:
        db.update_one({"entities.name": entity_name}, { '$inc': {'entities.$.count': -1} })
        print(entity_name + " => " + str(count - 1))
    else:
        delete_entity(entity_name)
        print(entity_name + " deleted.")
def delete_entity(entity_name):
    db.update_many({}, { '$pull': { "entities": {'name': entity_name} } })
def ensure_argc(count):
    if argc != count:
        error("invalid number of arguments")
def ensure_entity(entity):
    if not entity_exists(entity):
        error("no such entity exists")
def ensure_internet_connection():
    try:
        s = create_connection( (gethostbyname('one.one.one.one'), 80), 2 )
        s.close()
    except:
        error('no internet connection')
def entity_exists(name):
    for label in get_all_labels():
        for entity in entity_list(label):
            if entity['name'] == name:
                return True
    return False 
def entity_list(label):
    return db.find_one( {"label": label}, {"entities": 1, "_id": 0} )['entities']
def error(message):
    print("Error: " + message + ".")
    exit()
def get_all_labels():
    to_return = []
    for c in db.find({}, {"label": 1, "_id": 0}):
        to_return.append(c['label'])
    return to_return
def get_count():
    count = 0

    for label in get_all_labels():
        for _ in entity_list(label):
            count += 1
    return count
def get_entity_count(entity):
    return db.find_one(
        {"entities.name": entity}, { "_id": 0, 'entities': { '$elemMatch': {'name': entity} } }
    )['entities'][0]['count']
def get_highest_count():
    highest = 0

    for label in get_all_labels():
        for entity in db.find_one( {"label": label}, {"entities.count": 1, "_id": 0} )['entities']:
            count = int(entity['count'])

            if count > highest:
                highest = count
    return highest

if (argc == 1) or ( (argc == 2) and (argv[1] in ["-t", "--to-do", "--show-notes"]) ):
    if not db_len():
        print("No entries yet.")
    else:
        labels  = get_all_labels()
        highest = get_highest_count()
        
        onlyhighlighted = False
        all_notes       = False
        if argc == 2:
            if argv[1] in ["-t", "--to-do"]: 
                onlyhighlighted = True
            elif argv[1] == "--show-notes":
                all_notes = True

        for label in labels:
            if not onlyhighlighted:
                print(label)
            for entity in entity_list(label):
                count = int(entity['count'])
                name  = entity['name']
                notes = entity['note']

                if not onlyhighlighted:
                    _print("\t")
                if (count == highest) and not onlyhighlighted:
                    _print("\033[4m")
                if not onlyhighlighted:
                    _print("• " + name)
                else:
                    if count == highest:
                        _print(name)
                if (count != 0) and ( (not onlyhighlighted) or (count == highest) ):
                    _print(" x" + str(count))
                    if (onlyhighlighted or all_notes) and notes:
                        _print(" [" + entity['note'] + "]")
                if (count == highest) and not onlyhighlighted:
                    _print("\033[0m")
                if (not onlyhighlighted) or (count == highest):
                    print()
            if not onlyhighlighted:
                print()
else:
    if argv[1] in ["-h", "--help"]:
        print(dedent('''
            Usage: learnTrack [options]
            \t-v, --version                  : show version information.
            \t-h, --help                     : show this prompt.
            \t-a, --add <item> [label [count]: add an item.
            \t-i, ++ <item>                  : increment an item.
            \t+= <number> <item>             : increment <item> count by <number>
            \t-t, --to-do                    : list the highlighted items.
            \t-d, -- <item>                  : decrement an item.
            \t-re, --remove-entry <item>     : remove item from list.
            \t--show-notes                   : show the full list with notes
            \t-an, --add-note <item> <note>  : add/change note to/of item.
        '''))
    elif argv[1] in ['-v', "--version"]:
        print(
            "version: " + version +
            "\nmax items: " + str(maxitems)
        )
    elif argv[1] in ["-a", "--add"]:
        ensure_internet_connection()
        if (argc < 3) and (argc > 5):
            error("invalid number of arguments")
        if argc == 5:
            if not argv[4].isdigit():
                error("invalid argument `" + argv[4] + "`")
            count = int(argv[4])
        else:
            if not db_len():
                count = 0
            else:
                _count = 0
                _sum = 0

                for label in get_all_labels():
                    for entity in entity_list(label):
                        _count += 1
                        _sum += entity['count']
                count = int( round(_sum / _count) )

        if db_len():
            if entity_exists(argv[2]):
                error("item already exists")
        
        label = argv[3] if argc > 3 else "unlabeled"

        if not db.find_one({"label": label}):
            db.insert_one({"label": label, "entities": [{'name': argv[2], 'count': count, 'note': None}]})
        else:
            db.update_one({"label": label}, { '$push': { "entities": {'name': argv[2], 'count': count, 'note': None} } })
        print("Added.")

        #check if clean-up is needed
        while get_count() > maxitems:
            print("\nClean-up required.\n")
            for label in get_all_labels():
                for entity in entity_list(label):
                    decrement(entity['name'])
    elif argv[1] in ["-i", "++"]:
        ensure_argc(3)
        ensure_internet_connection()
        ensure_entity(argv[2])

        count = get_entity_count(argv[2])
        current_highest_count = get_highest_count()

        if count == current_highest_count:
            if list( db.aggregate([
                { '$match': {'entities.count': current_highest_count} },
                { '$project':
                    { "entities":
                        { '$filter':  {
                            "input": "$entities",
                            "as": "entity",
                            "cond": {'$eq': ['$$entity.count', current_highest_count]}
                        } }, '_id': 0 }
                }
            ]) )[0]['entities'].__len__() == 1:
                print("I can't let you do this, mortal.")
                exit()

        db.update_one({"entities.name": argv[2]}, { '$inc': {'entities.$.count': 1} })
        print(argv[2] + " => " + str(count + 1))
    elif argv[1] in ["-d", "--"]:
        ensure_argc(3)
        ensure_internet_connection()
        ensure_entity(argv[2])
        decrement(argv[2])
    elif argv[1] in ["--remove-entry", "-re"]:
        ensure_argc(3)
        ensure_internet_connection()
        ensure_entity(argv[2])

        label = db.find_one({"entities.name": argv[2]}, {"label": 1, "_id": 0})['label']
        delete_entity(argv[2])

        if not list(
            db.aggregate([{ '$match': {'label': label} }, { '$project': {'label': 1 , 'size': {'$size': '$entities'}} }])
        )[0]['size']:
            db.delete_one({'label': label})

        print(argv[2] + " deleted.")
    elif argv[1] in ["--add-note", "-an"]:
        ensure_argc(4)
        ensure_internet_connection()
        ensure_entity(argv[2])
        db.update_one({"entities.name": argv[2]}, { '$set': {'entities.$.note': argv[3]} })
        print("Note added.")