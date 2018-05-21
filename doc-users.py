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

## ------------------------------------------------- table -------------------------------------------------------------
#@ ### table


## ----------------------------------------------- queryset ------------------------------------------------------------
#@ ### queryset


## ------------------------------------------------ record -------------------------------------------------------------
#@ ### record

#@ #### get record
building = idf["Building"].one(lambda x: x["name"] == "Bldg")  # !! retains case (talk about case) !!
idf["Building"].one(lambda x: x["nAmE"] == "Bldg")
idf["Building"].one(lambda x: x[0] == "Bldg")

#@ #### add record
## todo: show table syntax
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


#@ #### remove record
idf.remove(new_sch)
print("found: ", len(idf["Schedule:Compact"].select(lambda x: x["name"] == "heating setpoint schedule - new")) == 1)


#@ #### display info
print(building.info(detailed=False))
print(building)

#@ #### get field value
#@ todo
## sch[-2] = "Until: 22:00"

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
