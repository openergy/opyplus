import oplus as op

idf = op.Epm(check_required=False)
bsd = idf.BuildingSurface_Detailed.add(name = "toto")
bsd.add_fields(1, 2, 3)
