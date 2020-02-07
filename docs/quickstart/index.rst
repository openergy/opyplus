Quickstart
==========


Installation
^^^^^^^^^^^^

opyplus can be installed using conda or pip:

.. code-block:: bash

    pip install opyplus

.. code-block:: bash

    conda install -c conda-forge opyplus

Examples
^^^^^^^^

Imports
-------

.. testcode::

    import tempfile
    temp_dir = tempfile.TemporaryDirectory()
    work_dir_path = temp_dir.name
    import os
    import opyplus as op

Epm
---
Load and save an idf file (loaded as an EnergyPlus Model, Epm)

.. testcode::

    idf_path = os.path.join(
        op.get_eplus_base_dir_path((9, 0, 1)),
        "ExampleFiles",
        "1ZoneEvapCooler.idf"
    )
    epm = op.Epm.load(idf_path)
    epm.save(os.path.join(work_dir_path, "my_idf.idf"))

Table
-----
A table is a collection of records of the same type.

.. testcode::

    zones = epm.Zone
    print(zones)
    print(f"\nzones: {len(zones)}\n")
    for z in zones:
        print(z.name)

.. testoutput::

    Table Zone (Zone)
      main zone

    zones: 1

    main zone

Queryset
--------

A queryset is the result of a select query on a table or another queryset.

.. testcode::

    # on a table
    qs = epm.Zone.select(lambda x: x.name == "main zone")

    # or another queryset
    qs = qs.select(lambda x: x.name == "main zone")

    print("records: ", qs)
    print("\niter:")
    for r in qs:
        print(r["name"])
    print("\nget item:")
    print(qs[0])

.. testoutput::

    records:  <Queryset of Zone: 1 records>

    iter:
    main zone

    get item:
    Zone,
        main zone,                     ! Name
        0.0,                           ! Direction of Relative North
        0.0,                           ! X Origin
        0.0,                           ! Y Origin
        0.0,                           ! Z Origin
        1,                             ! Type
        1,                             ! Multiplier
        autocalculate,                 ! Ceiling Height
        autocalculate;                 ! Volume

Record
------

Get a record

.. testcode::

    # from a table
    building = epm.Building.one(lambda x: x.name == "Bldg")
    # or from queryset
    building = epm.Building.select(lambda x: x["name"] == "Bldg").one()


Add a record to a table

.. testcode::

    # add from a table
    new_sch = epm.Schedule_Compact.add(
        name="Heating Setpoint Schedule - new[1]",
        schedule_type_limits_name="Any Number",
        field_1="Through: 12/31",
        field_2="For: AllDays",
        field_3="Until: 24:00,20.0"
    )

    print(
        "found: ",
        epm.Schedule_Compact.one(
            lambda x: x.name == "heating setpoint schedule - new[1]"
        ) is new_sch
    )

.. testoutput::

    found:  True

Extensible fields can also be added after creation

.. testcode::

    new_sch = epm.Schedule_Compact.add(
        name="Heating Setpoint Schedule - new[2]",
        schedule_type_limits_name="Any Number"
    )
    new_sch.add_fields(
        "Through: 12/31",
        "For: AllDays",
        "Until: 24:00,20.0"
    )


remove record

.. testcode::

    new_sch.delete()
    print("found: ", len(epm.Schedule_Compact.select(lambda x: x.name == "heating setpoint schedule - new[2]")) == 1)


.. testoutput::

    found:  False

batch add (and remove)

.. testcode::

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


.. testoutput::

    added:
    heating setpoint schedule - 0
    heating setpoint schedule - 1
    heating setpoint schedule - 2

display info

.. testcode::

    print(building.get_info())
    print("")
    print(building)


.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Building (Building)
     0: Name (name)
        * default: NONE
        * retaincase: 
     1: North Axis (north_axis)
        * default: 0.0
        * note: degrees from true North
        * type: real
        * units: deg
     2: Terrain (terrain)
        * default: Suburbs
        * key: Country; Suburbs; City; Ocean; Urban
        * note: Country=FlatOpenCountry | Suburbs=CountryTownsSuburbs | City=CityCenter | Ocean=body of water (5km) | Urban=Urban-Industrial-Forest
        * type: choice
     3: Loads Convergence Tolerance Value (loads_convergence_tolerance_value)
        * default: .04
        * maximum: .5
        * minimum>: 0.0
        * note: Loads Convergence Tolerance Value is a fraction of load
        * type: real
     4: Temperature Convergence Tolerance Value (temperature_convergence_tolerance_value)
        * default: .4
        * maximum: .5
        * minimum>: 0.0
        * type: real
        * units: deltaC
     5: Solar Distribution (solar_distribution)
        * default: FullExterior
        * key: MinimalShadowing; FullExterior; FullInteriorAndExterior; FullExteriorWithReflections; FullInteriorAndExteriorWithReflections
        * note: MinimalShadowing | FullExterior | FullInteriorAndExterior | FullExteriorWithReflections | FullInteriorAndExteriorWithReflections
        * type: choice
     6: Maximum Number of Warmup Days (maximum_number_of_warmup_days)
        * default: 25
        * minimum>: 0
        * note: EnergyPlus will only use as many warmup days as needed to reach convergence tolerance.; This field's value should NOT be set less than 25.
        * type: integer
     7: Minimum Number of Warmup Days (minimum_number_of_warmup_days)
        * default: 6
        * minimum>: 0
        * note: The minimum number of warmup days that produce enough temperature and flux history; to start EnergyPlus simulation for all reference buildings was suggested to be 6.; When this field is greater than the maximum warmup days defined previous field; the maximum number of warmup days will be reset to the minimum value entered here.; Warmup days will be set to be the value you entered when it is less than the default 6.
        * type: integer


    Building,
        Bldg,                          ! Name
        0.0,                           ! North Axis
        suburbs,                       ! Terrain
        0.05,                          ! Loads Convergence Tolerance Value
        0.05,                          ! Temperature Convergence Tolerance Value
        minimalshadowing,              ! Solar Distribution
        30,                            ! Maximum Number of Warmup Days
        6;                             ! Minimum Number of Warmup Days


get field value

.. testcode::

    print("name: ", building.name)
    print("name: ", building["name"])
    print("name: ", building[0])


.. testoutput::

    name:  Bldg
    name:  Bldg
    name:  Bldg

set basic field

.. testcode::

    old_name = building.terrain
    print(f"old name: {old_name}")

    building.terrain = "Downtown"
    print(f"new name: {building.terrain}")

    building.terrain = old_name



.. testoutput::

    old name: suburbs
    new name: downtown

replace basic fields

.. testcode::

    sch = epm.Schedule_Compact.one(lambda x: x.name == "heating setpoint schedule")

    sch.name = "Heating Setpoint Schedule"
    sch.field_1 = "Through: 12/31"
    sch[3] = "For: AllDays"  # index syntax

    print(sch)

    sch.name = "Heating Setpoint Schedule new_name"

    print(sch)



.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Schedule:Compact,
        heating setpoint schedule,     ! Name
        any number,                    ! Schedule Type Limits Name
        through: 12/31,                ! Field 0
        for: alldays,                  ! Field 1
        until: 24:00,                  ! Field 2
        20.0;                          ! Field 3

    Schedule:Compact,
        heating setpoint schedule new_name,    ! Name
        any number,                    ! Schedule Type Limits Name
        through: 12/31,                ! Field 0
        for: alldays,                  ! Field 1
        until: 24:00,                  ! Field 2
        20.0;                          ! Field 3


set record fields

.. testcode::

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


.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    ThermostatSetpoint:SingleHeating,
        heating setpoint,              ! Name
        heating setpoint schedule new_name;    ! Setpoint Temperature Schedule Name

    ThermostatSetpoint:SingleHeating,
        heating setpoint,              ! Name
        zone control type sched;       ! Setpoint Temperature Schedule Name

    ThermostatSetpoint:SingleHeating,
        heating setpoint,              ! Name
        heating setpoint schedule new_name;    ! Setpoint Temperature Schedule Name


add fields (only for extensibles)

.. testcode::

    sch.add_fields(
        "Until: 24:00",
        "25"
    )
    print(sch)


.. testoutput::

    Schedule:Compact,
        heating setpoint schedule new_name,    ! Name
        any number,                    ! Schedule Type Limits Name
        through: 12/31,                ! Field 0
        for: alldays,                  ! Field 1
        until: 24:00,                  ! Field 2
        20.0,                          ! Field 3
        until: 24:00,                  ! Field 4
        25;                            ! Field 5


explore links

.. testcode::

    pointing = sch.get_pointing_records()
    print("pointing on sch:")
    for _pointing in sch.get_pointing_records():
        print(_pointing)
    # todo: [GL] explore by table
    setpoint = pointing.ThermostatSetpoint_SingleHeating[0]
    print("pointed by setpoint:")
    for _pointed in setpoint.get_pointed_records():
        print(_pointed)
    # todo: [GL] explore by table


.. testoutput::

    pointing on sch:
    thermostatsetpoint_singleheating
    pointed by setpoint:
    schedule_compact

Simulation
----------
simulate

.. testcode::

    simulation_dir = os.path.join(work_dir_path, "simulation")
    if not os.path.isdir(simulation_dir):
        os.mkdir(simulation_dir)
    s = op.simulate(
        epm,
        os.path.join(
            op.get_eplus_base_dir_path((9, 0, 1)),
            "WeatherData",
            "USA_CO_Golden-NREL.724666_TMY3.epw"
        ),
        base_dir_path=simulation_dir
    )


standard output

.. testcode::

    # explore output
    eso = s.get_out_eso()
    print("info: \n", eso.get_info(), "\n")

    # explore environements
    print("environments: ", list(eso.get_environments().keys()), "\n")

    # explore variables
    print(f"variables: {eso.get_variables()}\n")

    # tuple instants dataframe
    df = eso.get_data()
    print(list(df.columns), "\n")
    print("index: ", df[["environment,Site Outdoor Air Drybulb Temperature"]].head(), "\n")

    # create datetime index
    eso.create_datetime_index(2014)

    # choose start year
    df = eso.get_data()
    print("datetime index: ",  df[["environment,Site Outdoor Air Drybulb Temperature"]].head(), "\n")

    # choose time step
    df = eso.get_data(frequency="hourly")

    # dump to csv for debug
    csv_dir_path = os.path.join(work_dir_path, "standard-output")
    eso.to_csv(csv_dir_path)
    print("standard-output content:")
    for name in sorted(os.listdir(csv_dir_path)):
        print(f"  {name}")


.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    info:
     Standard output
      environments
        denver centennial ann clg 1% condns db=>mwb (0)
          latitude: 39.74
          longitude: -105.18
          timezone_offset: -7.0
          elevation: 1829.0
        denver centennial ann htg 99.6% condns db (1)
          latitude: 39.74
          longitude: -105.18
          timezone_offset: -7.0
          elevation: 1829.0
        runperiod 1 (2)
          latitude: 39.74
          longitude: -105.18
          timezone_offset: -7.0
          elevation: 1829.0
      variables
        hourly
          environment,Site Outdoor Air Drybulb Temperature (7)
          environment,Site Outdoor Air Wetbulb Temperature (8)
          environment,Site Outdoor Air Humidity Ratio (9)
          environment,Site Outdoor Air Relative Humidity (10)
          main zone,Zone Mean Air Temperature (11)
          main zone baseboard,Baseboard Electric Power (160)
          supply inlet node,System Node Temperature (384)
          fan inlet node,System Node Temperature (385)
          evap cooler inlet node,System Node Temperature (386)
          supply outlet node,System Node Temperature (387)
          supply outlet node,System Node Mass Flow Rate (388)
          outside air inlet node,System Node Temperature (389)
          main zone outlet node,System Node Temperature (390)
          main zone node,System Node Temperature (391)
          main zone inlet node,System Node Temperature (392)
          zone equipment inlet node,System Node Temperature (393)
          zone equipment outlet node,System Node Temperature (394)
          relief air outlet node,System Node Temperature (395)


    environments:  ['denver centennial ann clg 1% condns db=>mwb', 'denver centennial ann htg 99.6% condns db', 'runperiod 1']

    variables: OrderedDict([('hourly', [environment,Site Outdoor Air Drybulb Temperature (7), environment,Site Outdoor Air Wetbulb Temperature (8), environment,Site Outdoor Air Humidity Ratio (9), environment,Site Outdoor Air Relative Humidity (10), main zone,Zone Mean Air Temperature (11), main zone baseboard,Baseboard Electric Power (160), supply inlet node,System Node Temperature (384), fan inlet node,System Node Temperature (385), evap cooler inlet node,System Node Temperature (386), supply outlet node,System Node Temperature (387), supply outlet node,System Node Mass Flow Rate (388), outside air inlet node,System Node Temperature (389), main zone outlet node,System Node Temperature (390), main zone node,System Node Temperature (391), main zone inlet node,System Node Temperature (392), zone equipment inlet node,System Node Temperature (393), zone equipment outlet node,System Node Temperature (394), relief air outlet node,System Node Temperature (395)])])

    ['month', 'day', 'hour', 'minute', 'end_minute', 'dst', 'day_type', 'environment,Site Outdoor Air Drybulb Temperature', 'environment,Site Outdoor Air Wetbulb Temperature', 'environment,Site Outdoor Air Humidity Ratio', 'environment,Site Outdoor Air Relative Humidity', 'main zone,Zone Mean Air Temperature', 'main zone baseboard,Baseboard Electric Power', 'supply inlet node,System Node Temperature', 'fan inlet node,System Node Temperature', 'evap cooler inlet node,System Node Temperature', 'supply outlet node,System Node Temperature', 'supply outlet node,System Node Mass Flow Rate', 'outside air inlet node,System Node Temperature', 'main zone outlet node,System Node Temperature', 'main zone node,System Node Temperature', 'main zone inlet node,System Node Temperature', 'zone equipment inlet node,System Node Temperature', 'zone equipment outlet node,System Node Temperature', 'relief air outlet node,System Node Temperature']

    index:     environment,Site Outdoor Air Drybulb Temperature
    0                                         -4.666667
    1                                         -3.000000
    2                                         -3.583333
    3                                         -2.833333
    4                                         -2.000000

    datetime index:                       environment,Site Outdoor Air Drybulb Temperature
    2014-01-01 00:00:00                                         -4.666667
    2014-01-01 01:00:00                                         -3.000000
    2014-01-01 02:00:00                                         -3.583333
    2014-01-01 03:00:00                                         -2.833333
    2014-01-01 04:00:00                                         -2.000000

    standard-output content:
      0#denver-centennial-ann-clg-1-condns-db-mwb#hourly.csv
      1#denver-centennial-ann-htg-99-6-condns-db#hourly.csv
      2#runperiod-1#hourly.csv

Weather data
------------

.. testcode::

    epw = op.WeatherData.load(os.path.join(
        op.get_eplus_base_dir_path((9, 0, 1)),
        "WeatherData",
        "USA_CO_Golden-NREL.724666_TMY3.epw")
    )

    # weather series
    df = epw.get_weather_series()
    print(list(df.columns))
    print(df[["drybulb"]].head())



.. testoutput::

    ['year', 'month', 'day', 'hour', 'minute', 'datasource', 'drybulb', 'dewpoint', 'relhum', 'atmos_pressure', 'exthorrad', 'extdirrad', 'horirsky', 'glohorrad', 'dirnorrad', 'difhorrad', 'glohorillum', 'dirnorillum', 'difhorillum', 'zenlum', 'winddir', 'windspd', 'totskycvr', 'opaqskycvr', 'visibility', 'ceiling_hgt', 'presweathobs', 'presweathcodes', 'precip_wtr', 'aerosol_opt_depth', 'snowdepth', 'days_last_snow', 'Albedo', 'liq_precip_depth', 'liq_precip_rate']
       drybulb
    0     -3.0
    1     -3.0
    2     -4.0
    3     -2.0
    4     -2.0

Case management
---------------

tables

.. testcode::

    # table refs have a case, but getitem on idf is case insensitive
    print("tables:")
    print(epm.Zone)
    print(epm.zOnE)


.. testoutput::

    tables:
    Table Zone (Zone)
      main zone
    Table Zone (Zone)
      main zone

record field keys

.. testcode::

    # record field keys are lower case with underscores instead of spaces
    print("building name:")
    print(building.name)
    print(building["name"])

.. testoutput::

    building name:
    Bldg
    Bldg

record field values

.. testcode::

    # some record field values retain case (are case sensitive) others not
    print(building.get_info())

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Building (Building)
     0: Name (name)
        * default: NONE
        * retaincase:
     1: North Axis (north_axis)
        * default: 0.0
        * note: degrees from true North
        * type: real
        * units: deg
     2: Terrain (terrain)
        * default: Suburbs
        * key: Country; Suburbs; City; Ocean; Urban
        * note: Country=FlatOpenCountry | Suburbs=CountryTownsSuburbs | City=CityCenter | Ocean=body of water (5km) | Urban=Urban-Industrial-Forest
        * type: choice
     3: Loads Convergence Tolerance Value (loads_convergence_tolerance_value)
        * default: .04
        * maximum: .5
        * minimum>: 0.0
        * note: Loads Convergence Tolerance Value is a fraction of load
        * type: real
     4: Temperature Convergence Tolerance Value (temperature_convergence_tolerance_value)
        * default: .4
        * maximum: .5
        * minimum>: 0.0
        * type: real
        * units: deltaC
     5: Solar Distribution (solar_distribution)
        * default: FullExterior
        * key: MinimalShadowing; FullExterior; FullInteriorAndExterior; FullExteriorWithReflections; FullInteriorAndExteriorWithReflections
        * note: MinimalShadowing | FullExterior | FullInteriorAndExterior | FullExteriorWithReflections | FullInteriorAndExteriorWithReflections
        * type: choice
     6: Maximum Number of Warmup Days (maximum_number_of_warmup_days)
        * default: 25
        * minimum>: 0
        * note: EnergyPlus will only use as many warmup days as needed to reach convergence tolerance.; This field's value should NOT be set less than 25.
        * type: integer
     7: Minimum Number of Warmup Days (minimum_number_of_warmup_days)
        * default: 6
        * minimum>: 0
        * note: The minimum number of warmup days that produce enough temperature and flux history; to start EnergyPlus simulation for all reference buildings was suggested to be 6.; When this field is greater than the maximum warmup days defined previous field; the maximum number of warmup days will be reset to the minimum value entered here.; Warmup days will be set to be the value you entered when it is less than the default 6.
        * type: integer


=> building name retains case, terrain doesn't

**Field values that don't retain case are always forced to lowercase. Field values that retain case keep their
case sensitive value.**

.. testcode::

    building.name = "StaysCamelCase"
    building.terrain = "Suburbs"  # will be set to lowercase
    print(building)

.. testoutput::

    Building,
        StaysCamelCase,                ! Name
        0.0,                           ! North Axis
        suburbs,                       ! Terrain
        0.05,                          ! Loads Convergence Tolerance Value
        0.05,                          ! Temperature Convergence Tolerance Value
        minimalshadowing,              ! Solar Distribution
        30,                            ! Maximum Number of Warmup Days
        6;                             ! Minimum Number of Warmup Days

don't forget these rules when filtering

.. testcode::

    print("retains, case not respected:", len(epm.Building.select(lambda x: x.name == "stayscamelcase")))  # not ok
    print("retains, case respected:", len(epm.Building.select(lambda x: x.name == "StaysCamelCase")))  # ok
    print("doesn't retain, uppercase: ", len(epm.Building.select(lambda x: x.terrain == "Suburbs")))  # not ok
    print("doesn't retain, lowercase: ", len(epm.Building.select(lambda x: x.terrain == "suburbs")))  # ok


.. testoutput::

    retains, case not respected: 0
    retains, case respected: 1
    doesn't retain, uppercase:  0
    doesn't retain, lowercase:  1
