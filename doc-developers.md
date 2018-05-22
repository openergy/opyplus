# oplus

## version refactoring

### 5.x => 6.x

useful pycharm replace in path (with regex):

    # __call__ => __getitem__
    idf\("([^"]*)"\)
    idf["$1"]
    
    # qs.one => table.one()
    (idf\["[^"]*"\])\.one
    $1.one()
    
    # [""].filter => .select
    (\["[^"]*"\])\.filter\("([^"]*)",([^\)]*)\)
    $1.select(lambda x: x["$2"] == $3)
    
    # .select(condition).one => .one(condition)
    \.select\(([^\)]*)\).one
    .one($1)
