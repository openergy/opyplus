 # oplus

 ## imports

	import os
	import oplus as op


 ## idf

 ### idf


	idf_path = os.path.join(
	    op.CONF.eplus_base_dir_path,
	    "ExampleFiles",
	    "1ZoneEvapCooler.idf"
	)

	idf = op.Idf(idf_path)
	idf.save_as(os.path.join(work_dir_path, "my_idf.idf"))
	print(idf)


*out:*

	<Idf: Bldg>

 ### table
 A table is a collection of records of the same type.


	zones = idf["Zone"]
	print(zones)
	print(f"\nzones: {len(zones)}\n")
	for z in zones:
	    print(z["name"])



*out:*

	<Table: Zone (1 records)>

	zones: 1

	main zone

 ### queryset
 A queryset is the result of a select query.


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


*out:*

	records:  <Queryset: [<Zone: main zone>]>

	iter:
	main zone

	get item:
	Zone,
	    main zone,                     ! - Name
	    0,                             ! - Direction of Relative North {deg}
	    0,                             ! - X Origin {m}
	    0,                             ! - Y Origin {m}
	    0,                             ! - Z Origin {m}
	    1,                             ! - Type
	    1,                             ! - Multiplier
	    autocalculate,                 ! - Ceiling Height {m}
	    autocalculate;                 ! - Volume {m3}


 ### record



 #### get record


	# directly from idf
	building = idf.one(lambda x: (x.table.ref == "Building") and (x["name"] == "Bldg"))

	# or from table
	building = idf["Building"].one(lambda x: x["name"] == "Bldg")

	# or from queryset
	building = idf["Building"].select(lambda x: x["name"] == "Bldg").one()



 #### add record


	# add from idf
	new_sch = idf.add(
	    """Schedule:Compact,
	    Heating Setpoint Schedule - new[1],  !- Name
	    Any Number,              !- Schedule Type Limits Name
	    Through: 12/31,          !- Field 1
	    For: AllDays,            !- Field 2
	    Until: 24:00,20.0;       !- Field 3
	    """
	)

	print("found: ", idf["Schedule:Compact"].one(lambda x: x["name"] == "heating setpoint schedule - new[1]") is new_sch)

	# or add from table
	new_sch = idf["Schedule:Compact"].add(
	    """Heating Setpoint Schedule - new[2],  !- Name
	    Any Number,              !- Schedule Type Limits Name
	    Through: 12/31,          !- Field 1
	    For: AllDays,            !- Field 2
	    Until: 24:00,20.0;       !- Field 3
	    """
	)


*out:*

	found:  True

 #### remove record

	idf.remove(new_sch)
	print("found: ", len(idf["Schedule:Compact"].select(lambda x: x["name"] == "heating setpoint schedule - new[2]")) == 1)


*out:*

	found:  False

 #### batch add (and remove)

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


*out:*

	added:
	heating setpoint schedule - 0
	heating setpoint schedule - 1
	heating setpoint schedule - 2

 #### display info

	print(building.info())
	print("")
	print(building)


*out:*

	--------
	Building
	--------
	0: Name
		* default: ['NONE']
		* retaincase: []
	1: North Axis
		* default: ['0.0']
		* note: degrees from true North
		* type: ['real']
		* units: ['deg']
	2: Terrain
		* default: ['Suburbs']
		* key: ['Country', 'Suburbs', 'City', 'Ocean', 'Urban']
		* note: Country=FlatOpenCountry | Suburbs=CountryTownsSuburbs | City=CityCenter | Ocean=body of water (5km) | Urban=Urban-Industrial-Forest
		* type: ['choice']
	3: Loads Convergence Tolerance Value
		* default: ['.04']
		* maximum: ['.5']
		* minimum>: ['0.0']
		* note: Loads Convergence Tolerance Value is a fraction of load
		* type: ['real']
	4: Temperature Convergence Tolerance Value
		* default: ['.4']
		* maximum: ['.5']
		* minimum>: ['0.0']
		* type: ['real']
		* units: ['deltaC']
	5: Solar Distribution
		* default: ['FullExterior']
		* key: ['MinimalShadowing', 'FullExterior', 'FullInteriorAndExterior', 'FullExteriorWithReflections', 'FullInteriorAndExteriorWithReflections']
		* note: MinimalShadowing | FullExterior | FullInteriorAndExterior | FullExteriorWithReflections | FullInteriorAndExteriorWithReflections
		* type: ['choice']
	6: Maximum Number of Warmup Days
		* default: ['25']
		* minimum>: ['0']
		* note: EnergyPlus will only use as many warmup days as needed to reach convergence tolerance. This field's value should NOT be set less than 25.
		* type: ['integer']
	7: Minimum Number of Warmup Days
		* default: ['6']
		* minimum>: ['0']
		* note: The minimum number of warmup days that produce enough temperature and flux history to start EnergyPlus simulation for all reference buildings was suggested to be 6. When this field is greater than the maximum warmup days defined previous field the maximum number of warmup days will be reset to the minimum value entered here. Warmup days will be set to be the value you entered when it is less than the default 6.
		* type: ['integer']

	Building,
	    Bldg,                          ! - Name
	    0.0,                           ! - North Axis {deg}
	    suburbs,                       ! - Terrain
	    0.05,                          ! - Loads Convergence Tolerance Value
	    0.05,                          ! - Temperature Convergence Tolerance Value {deltaC}
	    minimalshadowing,              ! - Solar Distribution
	    30,                            ! - Maximum Number of Warmup Days
	    6;                             ! - Minimum Number of Warmup Days


 #### get field value

	print("name: ", building["name"])
	print("name: ", building["nAmE"])
	print("name: ", building[0])


*out:*

	name:  Bldg
	name:  Bldg
	name:  Bldg

 #### set basic field

	old_name = building["TeRRain"]
	print(f"old name: {old_name}")

	building["terrain"] = "Downtown"
	print(f"new name: {building['terrain']}")

	building["terrain"] = old_name



*out:*

	old name: suburbs
	new name: downtown

 #### replace basic fields

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



*out:*

	Schedule:Compact,
	    heating setpoint schedule,     ! - Name
	    any number,                    ! - Schedule Type Limits Name
	    through: 1/31,                 ! - Field 1
	    for: alldays,                  ! - Field 2
	    until: 24:00,                  ! - Field 3
	    20.0,                          ! - Field 3
	    through: 12/31,                ! - Field 1
	    for: alldays,                  ! - Field 2
	    until: 24:00,
	    20.0;

	Schedule:Compact,
	    heating setpoint schedule,     ! - Name
	    any number,                    ! - Schedule Type Limits Name
	    through: 1/31,                 ! - Field 1
	    for: alldays,                  ! - Field 2
	    until: 24:00,                  ! - Field 3
	    30.0,                          ! - Field 3
	    through: 12/31,                ! - Field 1
	    for: alldays,                  ! - Field 2
	    until: 24:00,
	    20.0;


 #### set record fields

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


*out:*

	ThermostatSetpoint:SingleHeating,
	    heating setpoint,              ! - Name
	    heating setpoint schedule;     ! - Setpoint Temperature Schedule Name

	!! doesn't work !!

	ThermostatSetpoint:SingleHeating,
	    heating setpoint,              ! - Name
	    zone control type sched;       ! - Setpoint Temperature Schedule Name


 #### add fields

	sch.add_field("Until: 24:00", comment="added 1")
	sch.add_field("25")
	print(sch)



*out:*

	Schedule:Compact,
	    heating setpoint schedule,     ! - Name
	    any number,                    ! - Schedule Type Limits Name
	    through: 1/31,                 ! - Field 1
	    for: alldays,                  ! - Field 2
	    until: 24:00,                  ! - Field 3
	    30.0,                          ! - Field 3
	    through: 12/31,                ! - Field 1
	    for: alldays,                  ! - Field 2
	    until: 24:00,
	    20.0,
	    until: 24:00,                  ! added 1
	    25;


 #### explore links

	pointing = sch.pointing_records
	print("pointing on sch:")
	for _pointing in sch.pointing_records:
	    print(_pointing)

	setpoint = pointing[0]
	print("pointed by setpoint:")
	for _pointed in setpoint.pointed_records:
	    print(_pointed)



*out:*

	pointing on sch:
	ThermostatSetpoint:SingleHeating,
	    heating setpoint,              ! - Name
	    heating setpoint schedule;     ! - Setpoint Temperature Schedule Name

	pointed by setpoint:
	Schedule:Compact,
	    heating setpoint schedule,     ! - Name
	    any number,                    ! - Schedule Type Limits Name
	    through: 1/31,                 ! - Field 1
	    for: alldays,                  ! - Field 2
	    until: 24:00,                  ! - Field 3
	    30.0,                          ! - Field 3
	    through: 12/31,                ! - Field 1
	    for: alldays,                  ! - Field 2
	    until: 24:00,
	    20.0,
	    until: 24:00,                  ! added 1
	    25;


 ### case management



 #### tables

	# table refs have a case, but getitem on idf is case insensitive
	print("tables:")
	print(idf["Zone"])
	print(idf["zOnE"])


*out:*

	tables:
	<Table: Zone (1 records)>
	<Table: Zone (1 records)>

 #### record field keys

	# record field keys have a case, but getitem on a key is case insensitive
	print("\nbuilding name:")
	print(building["name"])
	print(building["nAmE"])


*out:*


	building name:
	Bldg
	Bldg

 #### record field values

	# some record field values retain case (are case sensitive) others not
	info = building.info(how="dict")
	print("Name: ", info["Name"])
	print("Terrain: ", info["Terrain"])


*out:*

	Name:  {'default': ['NONE'], 'retaincase': []}
	Terrain:  {'default': ['Suburbs'], 'key': ['Country', 'Suburbs', 'City', 'Ocean', 'Urban'], 'note': 'Country=FlatOpenCountry | Suburbs=CountryTownsSuburbs | City=CityCenter | Ocean=body of water (5km) | Urban=Urban-Industrial-Forest', 'type': ['choice']}

 => building name retains case, terrain doesn't

 **Field values that don't retain case are always forced to lowercase. Field values that retain case keep their
 case sensitive value.**


	building["name"] = "StaysCamelCase"
	building["terrain"] = "Suburbs"  # will be set to lowercase
	print(building)


*out:*

	Building,
	    StaysCamelCase,                ! - Name
	    0.0,                           ! - North Axis {deg}
	    suburbs,                       ! - Terrain
	    0.05,                          ! - Loads Convergence Tolerance Value
	    0.05,                          ! - Temperature Convergence Tolerance Value {deltaC}
	    minimalshadowing,              ! - Solar Distribution
	    30,                            ! - Maximum Number of Warmup Days
	    6;                             ! - Minimum Number of Warmup Days


 don't forget these rules when filtering


	print("retains, case not respected:", len(idf["Building"].select(lambda x: x["name"] == "stayscamelcase")))  # not ok
	print("retains, case respected:", len(idf["Building"].select(lambda x: x["name"] == "StaysCamelCase")))  # ok
	print("doesn't retain, uppercase: ", len(idf["Building"].select(lambda x: x["terrain"] == "Suburbs")))  # not ok
	print("doesn't retain, lowercase: ", len(idf["Building"].select(lambda x: x["terrain"] == "suburbs")))  # ok


*out:*

	retains, case not respected: 0
	retains, case respected: 1
	doesn't retain, uppercase:  0
	doesn't retain, lowercase:  1

 ## simulation

 ### simulate

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


 ### standard output

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



*out:*

	environments:  dict_keys(['SummerDesignDay', 'WinterDesignDay', 'RunPeriod']) 

	['day_type', 'dst', 'Environment,Site Outdoor Air Drybulb Temperature', 'Environment,Site Outdoor Air Wetbulb Temperature', 'Environment,Site Outdoor Air Humidity Ratio', 'Environment,Site Outdoor Air Relative Humidity', 'MAIN ZONE,Zone Mean Air Temperature', 'MAIN ZONE BASEBOARD,Baseboard Electric Power', 'SUPPLY INLET NODE,System Node Temperature', 'FAN INLET NODE,System Node Temperature', 'EVAP COOLER INLET NODE,System Node Temperature', 'SUPPLY OUTLET NODE,System Node Temperature', 'SUPPLY OUTLET NODE,System Node Mass Flow Rate', 'OUTSIDE AIR INLET NODE,System Node Temperature', 'MAIN ZONE OUTLET NODE,System Node Temperature', 'MAIN ZONE NODE,System Node Temperature', 'MAIN ZONE INLET NODE,System Node Temperature', 'ZONE EQUIPMENT INLET NODE,System Node Temperature', 'ZONE EQUIPMENT OUTLET NODE,System Node Temperature', 'RELIEF AIR OUTLET NODE,System Node Temperature'] 

	default index:                         Environment,Site Outdoor Air Drybulb Temperature
	month day hour minute                                                  
	1     1   1    60                                             -4.666667
	          2    60                                             -3.000000
	          3    60                                             -3.583333
	          4    60                                             -2.833333
	          5    60                                             -2.000000 

	datetime index:                       Environment,Site Outdoor Air Drybulb Temperature
	2014-01-01 01:00:00                                         -4.666667
	2014-01-01 02:00:00                                         -3.000000
	2014-01-01 03:00:00                                         -3.583333
	2014-01-01 04:00:00                                         -2.833333
	2014-01-01 05:00:00                                         -2.000000 

	Available data:
		SummerDesignDay: Hourly
		WinterDesignDay: Hourly
		RunPeriod: Hourly

 ### standard output

	epw = op.Epw(os.path.join(
	    op.configuration.CONF.eplus_base_dir_path,
	    "WeatherData",
	    "USA_CO_Golden-NREL.724666_TMY3.epw")
	)

	df = epw.df()
	print(list(df.columns))
	print(df[["drybulb"]].head())



*out:*

	['datasource', 'drybulb', 'dewpoint', 'relhum', 'atmos_pressure', 'exthorrad', 'extdirrad', 'horirsky', 'glohorrad', 'dirnorrad', 'difhorrad', 'glohorillum', 'dirnorillum', 'difhorillum', 'zenlum', 'winddir', 'windspd', 'totskycvr', 'opaqskycvr', 'visibility', 'ceiling_hgt', 'presweathobs', 'presweathcodes', 'precip_wtr', 'aerosol_opt_depth', 'snowdepth', 'days_last_snow', 'albedo', 'liq_precip_depth', 'liq_precip_rate']
	                            drybulb
	year month day hour minute         
	1999 1     1   1    0          -3.0
	               2    0          -3.0
	               3    0          -4.0
	               4    0          -2.0
	               5    0          -2.0


