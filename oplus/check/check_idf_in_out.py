import os
import tempfile

from oplus.configuration import CONF
from oplus.idf import IDF


idf = IDF(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))
zone = idf("Zone").filter("name", "Main Zone").one
building = idf("Building").filter("name", "Bldg").one

# check info
if True:
    print(idf.info(sort_by_group=False, detailed=True))

if True:
    print(zone.info(detailed=False))

# check to_str
if True:
    zone.head_comment = "Hello\n\n\nhello!!"
    zone.tail_comment = "Here is my tail comment\nwritten on several lines..."
    zone.field_comment(0, zone.field_comment(0) + " **modified with\nline\nbreaks**")
    print(zone.to_str(style="console"))  # idf, console

# check save_as
if True:
    # modify idf comment
    idf.comment = "I HAVE MODIFIED THE COMMENTS\n2 blank lines follow\n\n" + idf.comment

    # modify building
    building.head_comment = "MY BUILDING HEAD COMMENT"
    building.field_comment("terrain", building.field_comment("terrain") + " WITH MY NEW COMMENT")
    building.tail_comment = idf.comment

    f = tempfile.TemporaryFile("r+")
    idf.save_as(f)
    f.seek(0)
    print(f.read())
