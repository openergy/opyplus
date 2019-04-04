import tempfile


temp_dir = tempfile.TemporaryDirectory()
work_dir_path = temp_dir.name
work_dir_path = r"C:\Users\geoffroy.destaintot\Downloads\simu_doc"

#@ # oplus
#@
#@ ## imports
import os
import oplus as op

## ---------------------------------------------------------------------------------------------------------------------
## ------------------------------------------------- epm ---------------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------------------
#@ ## epm (Energy Plus Model)
#@
## ------------------------------------------------- epm ---------------------------------------------------------------
#@ ### epm

idf_path = os.path.join(
    op.CONF.eplus_base_dir_path,
    "ExampleFiles",
    "1ZoneEvapCooler.idf"
)

epm = op.Epm.from_idf(idf_path)
epm.to_idf(os.path.join(work_dir_path, "my_idf.idf"))
print(epm)

## ------------------------------------------------- table -------------------------------------------------------------
#@ ### table
#@ A table is a collection of records of the same type.

zones = epm.Zone
print(zones)
print(f"\nzones: {len(zones)}\n")
for z in zones:
    print(z.name)


## ----------------------------------------------- queryset ------------------------------------------------------------
#@ ### queryset
#@ A queryset is the result of a select query on a table.

# or a table
qs = epm.Zone.select(lambda x: x.name == "main zone")

# or another queryset
qs = qs.select(lambda x: x.name == "main zone")

print("records: ", qs)
print("\niter:")
for r in qs:
    print(r["name"])
print("\nget item:")
print(qs[0])

## ------------------------------------------------ record -------------------------------------------------------------
#@ ### record

#@ #### get record

# from a table
building = epm.Building.one(lambda x: x.name == "Bldg")
# or from queryset
building = epm.Building.select(lambda x: x["name"] == "Bldg").one()

#@ #### add record
print("ok")
# add from a table
new_sch = epm.Schedule_Compact.add(
    name="Heating Setpoint Schedule - new[1]",
    schedule_type_limits_name="Any Number",
    field_1="Through: 12/31",
    field_2="For: AllDays",
    field_3="Until: 24:00,20.0"
)

print("found: ", epm.Schedule_Compact.one(lambda x: x.name == "heating setpoint schedule - new[1]") is new_sch)

# may also add extensible fields in afterwards add from table (only for extensible records)
new_sch = epm.Schedule_Compact.add(
    name="Heating Setpoint Schedule - new[2]",
    schedule_type_limits_name="Any Number"
)
new_sch.add_fields(
    "Through: 12/31",
    "For: AllDays",
    "Until: 24:00,20.0"
)

#@ #### remove record
new_sch.delete()
print("found: ", len(epm.Schedule_Compact.select(lambda x: x.name == "heating setpoint schedule - new[2]")) == 1)

#@ #### batch add (and remove)
schedules = [
    dict(
        name="Heating Setpoint Schedule - 0",
        schedule_type_limits_name="Any Number",
        field_1="Through: 12/31",
        field_2="For: AllDays",
        field_3="Until: 24:00,20.0"
    ),
    dict(
        name="Heating Setpoint Schedule - 1",
        schedule_type_limits_name="Any Number",
        field_1="Through: 12/31",
        field_2="For: AllDays",
        field_3="Until: 24:00,20.0"
    ),
    dict(
        name="Heating Setpoint Schedule - 2",
        schedule_type_limits_name="Any Number",
        field_1="Through: 12/31",
        field_2="For: AllDays",
        field_3="Until: 24:00,20.0"
    ),
]

# idf syntax
added = epm.Schedule_Compact.batch_add(schedules)
print("added:")
for a in added:
    print(a["name"])

added.delete()

#@ #### display info
print(building.get_info())
print("")
print(building)

#@ #### get field value
print("name: ", building.name)
print("name: ", building["name"])
print("name: ", building[0])

#@ #### set basic field
old_name = building.terrain
print(f"old name: {old_name}")

building.terrain = "Downtown"
print(f"new name: {building.terrain}")

building.terrain = old_name


#@ #### replace basic fields
sch = epm.Schedule_Compact.one(lambda x: x.name == "heating setpoint schedule")

sch.name = "Heating Setpoint Schedule"
sch.field_1 = "Through: 12/31"
sch[3] = "For: AllDays"  # index syntax

print(sch)

sch.name = "Heating Setpoint Schedule new_name"

print(sch)


#@ #### set record fields
# work with setpoint record
setpoint = epm.ThermostatSetpoint_SingleHeating.one(lambda x: x.name == "heating setpoint")
print(setpoint)

# can set directly by name
setpoint.setpoint_temperature_schedule_name = "zone control type sched"
print(setpoint)

# or set record
new_sch = epm.Schedule_Compact.one(lambda x: x["name"] == "heating setpoint schedule new_name")
setpoint.setpoint_temperature_schedule_name = new_sch
print(setpoint)

# reset old value
setpoint.setpoint_temperature_schedule_name = sch

#@ #### add fields (only for extensibles)
sch.add_fields(
    "Until: 24:00",
    "25"
)
print(sch)

#@ #### explore links
pointing = sch.get_pointing_records()
print("pointing on sch:")
for _pointing in sch.get_pointing_records():
    print(_pointing)
# todo: explore by table
setpoint = pointing.ThermostatSetpoint_SingleHeating[0]
print("pointed by setpoint:")
for _pointed in setpoint.get_pointed_records():
    print(_pointed)
# todo: explore by table

## ------------------------------------------ case management ----------------------------------------------------------
#@ ### case management

#@ #### tables
# table refs have a case, but getitem on idf is case insensitive
print("tables:")
print(epm.Zone)
print(epm.zOnE)

#@ #### record field keys
# record field keys are lower case with underscores instead of spaces
print("\nbuilding name:")
print(building.name)
print(building["name"])

#@ #### record field values
# some record field values retain case (are case sensitive) others not
print(building.get_info())

#@ => building name retains case, terrain doesn't
#@
#@ **Field values that don't retain case are always forced to lowercase. Field values that retain case keep their
#@ case sensitive value.**

building.name = "StaysCamelCase"
building.terrain = "Suburbs"  # will be set to lowercase
print(building)

#@ don't forget these rules when filtering

print("retains, case not respected:", len(epm.Building.select(lambda x: x.name == "stayscamelcase")))  # not ok
print("retains, case respected:", len(epm.Building.select(lambda x: x.name == "StaysCamelCase")))  # ok
print("doesn't retain, uppercase: ", len(epm.Building.select(lambda x: x.terrain == "Suburbs")))  # not ok
print("doesn't retain, lowercase: ", len(epm.Building.select(lambda x: x.terrain == "suburbs")))  # ok

## ---------------------------------------------------------------------------------------------------------------------
## ---------------------------------------------- simulation -----------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------------------
#@ ## simulation
#@
## ----------------------------------------------- simulate ------------------------------------------------------------
#@ ### simulate
simulation_dir = os.path.join(work_dir_path, "simulation")
if not os.path.isdir(simulation_dir):
    os.mkdir(simulation_dir)
s = op.simulate(
    epm,
    os.path.join(
        op.CONF.eplus_base_dir_path,
        "WeatherData",
        "USA_CO_Golden-NREL.724666_TMY3.epw"
    ),
    base_dir_path=simulation_dir
)

## -------------------------------------------- standard output --------------------------------------------------------
#@ ### standard output
# explore output
print("info: \n", s.eso.get_info(), "\n")

# explore environements
print("environments: ", s.eso.get_environments(), "\n")

# explore variables
print(f"variables: {s.eso.get_variables()}\n")

# tuple instants dataframe
df = s.eso.get_data()
print(list(df.columns), "\n")
print("default index: ", df[["environment,Site Outdoor Air Drybulb Temperature"]].head(), "\n")


# switch to datetime instants
s.eso.switch_to_datetime_instants(2014)

# choose start year
df = s.eso.get_data()
print("datetime index: ",  df[["environment,Site Outdoor Air Drybulb Temperature"]].head(), "\n")

# choose time step
df = s.eso.get_data(frequency="hourly")


## -------------------------------------------- weather data -----------------------------------------------------------
#@ ### weather data
epw = op.WeatherData.from_epw(os.path.join(
    op.configuration.CONF.eplus_base_dir_path,
    "WeatherData",
    "USA_CO_Golden-NREL.724666_TMY3.epw")
)

# tuple index
df = epw.get_weather_series()
print(list(df.columns))
print(df[["drybulb"]].head())


## ---------------------------------------------------------------------------------------------------------------------
## ----------------------------------------------- cleanup -------------------------------------------------------------
## ---------------------------------------------------------------------------------------------------------------------
#@
temp_dir.cleanup()
