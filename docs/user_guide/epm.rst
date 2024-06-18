EPlus Model (idf file)
======================

An EnergyPlus Model (Epm) is a python object describing a building model (idf or epjson file).
This object contains tables, which contain records.

Epm
^^^

.. testsetup::

    import os
    import tempfile
    initial_cwd = os.getcwd()
    temp_dir = tempfile.TemporaryDirectory()
    os.chdir(temp_dir.name)

Perform imports, and prepare EPlus base directory path (to work with example files).

.. testcode::

    import os
    import opyplus as op

    eplus_dir_path = op.get_eplus_base_dir_path((22,1,0))


Load Epm

.. testcode::

    # prepare path
    idf_path = os.path.join(
        eplus_dir_path,
        "ExampleFiles",
        "1ZoneEvapCooler.idf"
    )

    # load epm
    epm = op.Epm.load(idf_path)

    print(epm)

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Epm
      AirLoopHVAC: 1 record
      AirLoopHVAC:ControllerList: 1 record
      AirLoopHVAC:OutdoorAirSystem: 1 record
      AirLoopHVAC:OutdoorAirSystem:EquipmentList: 1 record
      AirLoopHVAC:ReturnPath: 1 record
      AirLoopHVAC:SupplyPath: 1 record
      AirLoopHVAC:ZoneMixer: 1 record
      AirLoopHVAC:ZoneSplitter: 1 record
      AirTerminal:SingleDuct:ConstantVolume:NoReheat: 1 record
      AvailabilityManager:HighTemperatureTurnOn: 1 record
      AvailabilityManager:LowTemperatureTurnOff: 1 record
      AvailabilityManagerAssignmentList: 1 record
      Branch: 1 record
      BranchList: 1 record
      Building: 1 record
      BuildingSurface:Detailed: 6 records
      Construction: 3 records
      Controller:OutdoorAir: 1 record
      EvaporativeCooler:Direct:CelDekPad: 1 record
      Fan:ConstantVolume: 1 record
      GlobalGeometryRules: 1 record
      HeatBalanceAlgorithm: 1 record
      Material: 1 record
      Material:NoMass: 2 records
      OutdoorAir:Mixer: 1 record
      OutdoorAir:Node: 1 record
      Output:Constructions: 1 record
      Output:Meter:MeterFileOnly: 4 records
      Output:Surfaces:Drawing: 1 record
      Output:Table:SummaryReports: 1 record
      Output:Variable: 8 records
      Output:VariableDictionary: 1 record
      OutputControl:Table:Style: 1 record
      RunPeriod: 1 record
      Schedule:Compact: 4 records
      ScheduleTypeLimits: 2 records
      SimulationControl: 1 record
      Site:GroundTemperature:BuildingSurface: 1 record
      Site:Location: 1 record
      SizingPeriod:DesignDay: 2 records
      SurfaceConvectionAlgorithm:Inside: 1 record
      SurfaceConvectionAlgorithm:Outside: 1 record
      ThermostatSetpoint:SingleHeating: 1 record
      Timestep: 1 record
      Version: 1 record
      Zone: 1 record
      ZoneControl:Thermostat: 1 record
      ZoneHVAC:AirDistributionUnit: 1 record
      ZoneHVAC:Baseboard:Convective:Electric: 1 record
      ZoneHVAC:EquipmentConnections: 1 record
      ZoneHVAC:EquipmentList: 1 record
      ZoneInfiltration:DesignFlowRate: 1 record


Save Epm in a new file

.. testcode::

    epm.save("my_idf.idf")

Table
^^^^^

A table is a collection of records of the same type.


Retrieve and explore the zone table.

.. testcode::

    zones = epm.Zone
    print(zones)
    print(f"\nzones: {len(zones)}\n")
    for z in zones:
        print(z.name)

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Table Zone (Zone)
      main zone

    zones: 1

    main zone

Queryset
^^^^^^^^

 A queryset is the result of a select query on a table.

.. testcode::

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

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

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

Records
^^^^^^^

Get record
**********

.. testcode::

    # from a table
    building = epm.Building.one(lambda x: x.name == "Bldg")
    # or from queryset
    building = epm.Building.select(lambda x: x["name"] == "Bldg").one()

Add record
**********

.. testcode::

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

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    found:  True

Remove record
*************

.. testcode::

    new_sch.delete()
    print("found: ", len(epm.Schedule_Compact.select(lambda x: x.name == "heating setpoint schedule - new[2]")) == 1)

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    found:  False

Batch add (and remove)
**********************

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
    :options: +NORMALIZE_WHITESPACE

    added:
    heating setpoint schedule - 0
    heating setpoint schedule - 1
    heating setpoint schedule - 2

Display info
************

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
        * note: Loads Convergence Tolerance Value is a change in load from one warmup day to the next
        * type: real
        * units: W
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
        * default: 1
        * minimum>: 0
        * note: The minimum number of warmup days that produce enough temperature and flux history; to start EnergyPlus simulation for all reference buildings was suggested to be 6.; However this can lead to excessive run times as warmup days can be repeated needlessly.; For faster execution rely on the convergence criteria to detect when warmup is complete.; When this field is greater than the maximum warmup days defined previous field; the maximum number of warmup days will be reset to the minimum value entered here.; Warmup days will be set to be the value you entered. The default is 1.
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




Get field value
***************

.. testcode::

    print("name: ", building.name)
    print("name: ", building["name"])
    print("name: ", building[0])

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    name:  Bldg
    name:  Bldg
    name:  Bldg

Set basic field
***************

.. testcode::

    old_name = building.terrain
    print(f"old name: {old_name}")

    building.terrain = "Downtown"
    print(f"new name: {building.terrain}")

    building.terrain = old_name

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    old name: suburbs
    new name: downtown


Replace basic fields
********************

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
        through: 12/31,                ! Field 1
        for: alldays,                  ! Field 2
        until: 24:00,                  ! Field 3
        20.0;                          ! Field 4

    Schedule:Compact,
        heating setpoint schedule new_name,    ! Name
        any number,                    ! Schedule Type Limits Name
        through: 12/31,                ! Field 1
        for: alldays,                  ! Field 2
        until: 24:00,                  ! Field 3
        20.0;                          ! Field 4


Set record fields
*****************

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

Add fields (only for extensibles)
*********************************

.. testcode::

    sch.add_fields(
        "Until: 24:00",
        "25"
    )
    print(sch)

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Schedule:Compact,
        heating setpoint schedule new_name,    ! Name
        any number,                    ! Schedule Type Limits Name
        through: 12/31,                ! Field 1
        for: alldays,                  ! Field 2
        until: 24:00,                  ! Field 3
        20.0,                          ! Field 4
        until: 24:00,                  ! Field 5
        25;                            ! Field 6

Explore links
*************

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
    :options: +NORMALIZE_WHITESPACE

    pointing on sch:
    thermostatsetpoint_singleheating
    pointed by setpoint:
    schedule_compact

Case sensitivity
^^^^^^^^^^^^^^^^

Table names
***********

Table refs have a case, but getitem on idf is case insensitive

.. testcode::

    print("tables:")
    print(epm.Zone)
    print(epm.zOnE)

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    tables:
    Table Zone (Zone)
      main zone
    Table Zone (Zone)
      main zone

Record field keys
*****************

Record field keys are lower case with underscores instead of spaces

.. testcode::

    # todo: put an example with spaces
    print("\nbuilding name:")
    print(building.name)
    print(building["name"])

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    building name:
    Bldg
    Bldg

Record field values
*******************

In Energy Plus, some record field values retain case (are case sensitive) and others don't

.. testcode::

    print(building.get_info())
    # => building name retains case, terrain doesn't

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
        * note: Loads Convergence Tolerance Value is a change in load from one warmup day to the next
        * type: real
        * units: W
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
        * default: 1
        * minimum>: 0
        * note: The minimum number of warmup days that produce enough temperature and flux history; to start EnergyPlus simulation for all reference buildings was suggested to be 6.; However this can lead to excessive run times as warmup days can be repeated needlessly.; For faster execution rely on the convergence criteria to detect when warmup is complete.; When this field is greater than the maximum warmup days defined previous field; the maximum number of warmup days will be reset to the minimum value entered here.; Warmup days will be set to be the value you entered. The default is 1.
        * type: integer


.. note:: Field values that don't retain case are always forced to lowercase. Field values that retain case keep their case sensitive value.


.. testcode::

    building.name = "StaysCamelCase"
    building.terrain = "Suburbs"  # will be set to lowercase
    print(building)

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Building,
        StaysCamelCase,                ! Name
        0.0,                           ! North Axis
        suburbs,                       ! Terrain
        0.05,                          ! Loads Convergence Tolerance Value
        0.05,                          ! Temperature Convergence Tolerance Value
        minimalshadowing,              ! Solar Distribution
        30,                            ! Maximum Number of Warmup Days
        6;                             ! Minimum Number of Warmup Days


.. note:: Don't forget these rules when filtering

.. testcode::

    print("retains, case not respected:", len(epm.Building.select(lambda x: x.name == "stayscamelcase")))  # not ok
    print("retains, case respected:", len(epm.Building.select(lambda x: x.name == "StaysCamelCase")))  # ok
    print("doesn't retain, uppercase: ", len(epm.Building.select(lambda x: x.terrain == "Suburbs")))  # not ok
    print("doesn't retain, lowercase: ", len(epm.Building.select(lambda x: x.terrain == "suburbs")))  # ok

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    retains, case not respected: 0
    retains, case respected: 1
    doesn't retain, uppercase:  0
    doesn't retain, lowercase:  1

.. testcleanup::

    # come back to initial cwd
    os.chdir(initial_cwd)
