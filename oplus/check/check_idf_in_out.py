import os
import tempfile

from oplus.configuration import CONF
from oplus import Epm


idf = Epm(os.path.join(CONF.eplus_base_dir_path, "ExampleFiles", "1ZoneEvapCooler.idf"))
zone = idf["Zone"].one(lambda x: x["name"] == "Main Zone")
building = idf["Building"].one(lambda x: x["name"] == "Bldg")

# check info
if True:
    print(idf.get_info(sort_by_group=False, detailed=True))

if True:
    print(zone.get_info(detailed=False))

# check to_str
if True:
    zone.set_head_comment("Hello\n\n\nhello!!")
    zone.set_tail_comment("Here is my tail comment\nwritten on several lines...")
    zone.set_field_comment(0, zone.get_field_comment(0) + " **modified with\nline\nbreaks**")
    print(zone.to_idf(style="console"))  # idf, console

# check save_as
if True:
    # modify idf comment
    idf.set_comment("I HAVE MODIFIED THE COMMENTS\n2 blank lines follow\n\n" + idf.get_comment())

    # modify building
    building.set_head_comment("MY BUILDING HEAD COMMENT")
    building.set_field_comment("terrain", building.get_field_comment("terrain") + " WITH MY NEW COMMENT")
    building.set_tail_comment(idf.get_comment())

    f = tempfile.TemporaryFile("r+")
    idf.save_as(f)
    f.seek(0)
    print(f.read())
