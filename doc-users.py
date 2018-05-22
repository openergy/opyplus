import tempfile


temp_dir = tempfile.TemporaryDirectory()
work_dir_path = temp_dir.name


#@ # oplus
#@
#@ ## imports
import os
import oplus as op

## ---------------------------------------------------------------------------------------------------------------------
## ------------------------------------------------- idf ---------------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------------------
#@ ## idf
#@
## ------------------------------------------------- idf ---------------------------------------------------------------
#@ ### idf

idf_path = os.path.join(
    op.CONF.eplus_base_dir_path,
    "ExampleFiles",
    "1ZoneEvapCooler.idf"
)

idf = op.Idf(idf_path)
idf.save_as(os.path.join(work_dir_path, "my_idf.idf"))
print(idf)

## ------------------------------------------------- table -------------------------------------------------------------
#@ ### table
#@ A table is a collection of records of the same type.

zones = idf["Zone"]
print(zones)
print(f"\nzones: {len(zones)}\n")
for z in zones:
    print(z["name"])


## ----------------------------------------------- queryset ------------------------------------------------------------
#@ ### queryset
#@ A queryset is the result of a select query.

# query may be performed on an idf
qs = idf.select(lambda x: x.table.ref == "Zone" and x["name"] == "main zone")

# or a table
qs = idf["Zone"].select(lambda x: x["name"] == "main zone")

# or another queryset
qs = qs.select(lambda x: x["name"] == "main zone")

print("records: ", qs)
print("\niter:")
for r in qs:
    print(r["name"])
print("\nget item:")
print(qs[0])

## ------------------------------------------------ record -------------------------------------------------------------
#@ ### record

#@ #### get record

# directly from idf
building = idf.one(lambda x: (x.table.ref == "Building") and (x["name"] == "Bldg"))

# or from table
building = idf["Building"].one(lambda x: x["name"] == "Bldg")

# or from queryset
building = idf["Building"].select(lambda x: x["name"] == "Bldg").one()


#@ #### add record

# add from idf
new_sch = idf.add(
    """Schedule:Compact,
    Heating Setpoint Schedule - new,  !- Name
    Any Number,              !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00,20.0;       !- Field 3
    """
)

print("found: ", idf["Schedule:Compact"].one(lambda x: x["name"] == "heating setpoint schedule - new") is new_sch)

# or add from table
new_sch = idf["Schedule:Compact"].add(
    """Heating Setpoint Schedule - new2,  !- Name
    Any Number,              !- Schedule Type Limits Name
    Through: 12/31,          !- Field 1
    For: AllDays,            !- Field 2
    Until: 24:00,20.0;       !- Field 3
    """
)

#@ #### remove record
idf.remove(new_sch)
print("found: ", len(idf["Schedule:Compact"].select(lambda x: x["name"] == "heating setpoint schedule - new")) == 1)

#@ #### batch add (and remove)
schedules = [
    """Schedule:Compact,
        Heating Setpoint Schedule - 0,  !- Name
        Any Number,              !- Schedule Type Limits Name
        Through: 12/31,          !- Field 1
        For: AllDays,            !- Field 2
        Until: 24:00,20.0;       !- Field 3
    """,
    """Schedule:Compact,
        Heating Setpoint Schedule - 1,  !- Name
        Any Number,              !- Schedule Type Limits Name
        Through: 12/31,          !- Field 1
        For: AllDays,            !- Field 2
        Until: 24:00,20.0;       !- Field 3
    """,
    """Schedule:Compact,
        Heating Setpoint Schedule - 2,  !- Name
        Any Number,              !- Schedule Type Limits Name
        Through: 12/31,          !- Field 1
        For: AllDays,            !- Field 2
        Until: 24:00,20.0;       !- Field 3
    """
]

# idf syntax
added = idf.add(schedules)
print("added:")
for a in added:
    print(a["name"])

idf.remove(added)

# or table syntax
truncated_schedules = ["\n".join(s.split("\n")[1:]) for s in schedules]
added = idf["Schedule:Compact"].add(truncated_schedules)
idf["Schedule:Compact"].remove(added)

#@ #### display info
print(building.info())
print("")
print(building)

#@ #### get field value
print("name: ", building["name"])
print("name: ", building["nAmE"])
print("name: ", building[0])

#@ #### set basic field
old_name = building["TeRRain"]
print(f"old name: {old_name}")

building["terrain"] = "Downtown"
print(f"new name: {building['terrain']}")

building["terrain"] = old_name


#@ #### replace basic fields
sch = idf["Schedule:Compact"].one(lambda x: x["name"] == "heating setpoint schedule")
sch.replace_values(
    """Schedule:Compact,
        Heating Setpoint Schedule,  !- Name
        Any Number,              !- Schedule Type Limits Name
        Through: 1/31,          !- Field 1
        For: AllDays,            !- Field 2
        Until: 24:00,20.0,       !- Field 3
        Through: 12/31,          !- Field 1
        For: AllDays,            !- Field 2
        Until: 24:00,20.0;
        """
)
print(sch)

sch.replace_values(
    """Schedule:Compact,
        Heating Setpoint Schedule qsofjqsd ,  !- Name
        Any Number,              !- Schedule Type Limits Name
        Through: 1/31,          !- Field 1
        For: AllDays,            !- Field 2
        Until: 24:00,30.0,       !- Field 3
        Through: 12/31,          !- Field 1
        For: AllDays,            !- Field 2
        Until: 24:00,20.0;
        """
)

print(sch)


#@ #### set record fields
# work with setpoint record
setpoint = idf["ThermostatSetpoint:SingleHeating"].one(lambda x: x["name"] == "heating setpoint")
print(setpoint)

# can't set directly by name
try:
    setpoint["Setpoint Temperature Schedule Name"] = "zone control type sched"
except KeyError:
    print("!! doesn't work !!\n")

# must set record
new_sch = idf["Schedule:Compact"].one(lambda x: x["name"] == "zone control type sched")
setpoint["Setpoint Temperature Schedule Name"] = new_sch
print(setpoint)

# reset old value
setpoint["Setpoint Temperature Schedule Name"] = sch

#@ #### add fields
sch.add_field("Until: 24:00", comment="added 1")
sch.add_field("25")
print(sch)


#@ #### explore links
pointing = sch.pointing_records
print("pointing on sch:")
for _pointing in sch.pointing_records:
    print(_pointing)

setpoint = pointing[0]
print("pointed by setpoint:")
for _pointed in setpoint.pointed_records:
    print(_pointed)


## ------------------------------------------ case management ----------------------------------------------------------
#@ ### case management

#@ #### tables
# table refs have a case, but getitem on idf is case insensitive
print("tables:")
print(idf["Zone"])
print(idf["zOnE"])

#@ #### record field keys
# record field keys have a case, but getitem on a key is case insensitive
print("\nbuilding name:")
print(building["name"])
print(building["nAmE"])

#@ #### record field values
# some record field values retain case (are case sensitive) others not
info = building.info(how="dict")
print("Name: ", info["Name"])
print("Terrain: ", info["Terrain"])

#@ => building name retains case, terrain doesn't
#@
#@ **Field values that don't retain case are always forced to lowercase. Field values that retain case keep their
#@ case sensitive value.**

building["name"] = "StaysCamelCase"
building["terrain"] = "Suburbs"  # will be set to lowercase
print(building)

#@ don't forget these rules when filtering

print("retains, case not respected:", len(idf["Building"].select(lambda x: x["name"] == "stayscamelcase")))  # not ok
print("retains, case respected:", len(idf["Building"].select(lambda x: x["name"] == "StaysCamelCase")))  # ok
print("doesn't retain, uppercase: ", len(idf["Building"].select(lambda x: x["terrain"] == "Suburbs")))  # not ok
print("doesn't retain, lowercase: ", len(idf["Building"].select(lambda x: x["terrain"] == "suburbs")))  # ok

## ---------------------------------------------------------------------------------------------------------------------
## ---------------------------------------------- simulation -----------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------------------
#@ ## simulation
#@
## ----------------------------------------------- simulate ------------------------------------------------------------
#@ ### simulate
simulation_dir = os.path.join(work_dir_path, "simulation")
os.mkdir(simulation_dir)
s = op.simulate(
    idf,
    os.path.join(
        op.CONF.eplus_base_dir_path,
        "WeatherData",
        "USA_CO_Golden-NREL.724666_TMY3.epw"
    ),
    base_dir_path=simulation_dir
)

## -------------------------------------------- standard output --------------------------------------------------------
#@ ### standard output
# explore environements
print("environments: ", s.eso.environments, "\n")

# default dataframe
df = s.eso.df()
print(list(df.columns), "\n")
print("default index: ", df[["Environment,Site Outdoor Air Drybulb Temperature"]].head(), "\n")

# choose start year
df = s.eso.df(start=2014)
print("datetime index: ",  df[["Environment,Site Outdoor Air Drybulb Temperature"]].head(), "\n")

# get info
print(s.eso.info())

# choose time step
df = s.eso.df(time_step="Hourly")


## -------------------------------------------------- epw --------------------------------------------------------------
#@ ### standard output
epw = op.Epw(os.path.join(
    op.configuration.CONF.eplus_base_dir_path,
    "WeatherData",
    "USA_CO_Golden-NREL.724666_TMY3.epw")
)

df = epw.df()
print(list(df.columns))
print(df[["drybulb"]].head())


## ---------------------------------------------------------------------------------------------------------------------
## ----------------------------------------------- cleanup -------------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------------------
#@
temp_dir.cleanup()
