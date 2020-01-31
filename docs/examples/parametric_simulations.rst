Parametric simulations
======================

Imports
-------

.. testcode::

    import tempfile
    temp_dir = tempfile.TemporaryDirectory()
    work_dir_path = temp_dir.name
    import os
    import opyplus as op

Load File
---------

.. testcode::

    example_idf_path = os.path.join(
        op.get_eplus_base_dir_path((9, 0, 1)),
        "ExampleFiles",
        "RefBldgFullServiceRestaurantNew2004_Chicago.idf"
        )
    epm = op.Epm.load(example_idf_path)


Modify uses and save your models
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. testcode::

    alpha = 1.1
    for light in epm.Lights:
        light.watts_per_zone_floor_area *= alpha
    for ee in epm.ElectricEquipment:
        ee.design_level *= alpha

    epm.save(f"RefBldgFullServiceRestaurantNew2004_Chicago_'{alpha}.idf")


Modify temperature heating setpoint
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

simple example set all value

.. testcode::

    ## get all heating setpoint for ThermostatSetpoint:DualSetpoint object
    heating_setpoint_temperature_list = []
    for th_ds in epm.ThermostatSetpoint_DualSetpoint:
        heating_setpoint_temperature_list.append(th_ds.heating_setpoint_temperature_schedule_name)
    ## loop on and replace value
    for hsch in set(heating_setpoint_temperature_list):
        hsch.update({
            0: hsch[0],
            1: hsch[1],
            2: "through: 12/31",
            3: "for alldays",
            4: "until: 05:00",
            5: "16"
            4: "until: 19:00",
            5: "21"
            4: "until: 24:00",
            5: "16"
        })

expert example - find upper value and modify it

.. testcode::

    ## get all heating setpoint for ThermostatSetpoint:DualSetpoint object
    heating_setpoint_temperature_list = []
    for th_ds in epm.ThermostatSetpoint_DualSetpoint:
        heating_setpoint_temperature_list.append(th_ds.heating_setpoint_temperature_schedule_name)
    ## loop on
    for hsch in set(heating_setpoint_temperature_list):
        print("*** before")
        print(hsch)
        schedule_dict = hsch.to_dict()
        first_index = max(schedule_dict, key=lambda key: float(schedule_dict[key]) if isinstance(schedule_dict[key], str) and schedule_dict[key].isdigit() else 0)
        for i,v in schedule_dict.items():
            if v == schedule_dict[index]:
                hsch[i] = str(float(schedule_dict[index]) + 1)
        print("*** after")
        print(hsch)

.. testoutput::

   *** before
    Schedule:Compact,
        htgsetp_sch,                   ! Name
        temperature,                   ! Schedule Type Limits Name
        through: 12/31,                ! Field 0
        for: summerdesignday,          ! Field 1
        until: 24:00,                  ! Field 2
        15.6,                          ! Field 3
        for: winterdesignday,          ! Field 4
        until: 24:00,                  ! Field 5
        21,                            ! Field 6
        for: allotherdays,             ! Field 7
        until: 01:00,                  ! Field 8
        21,                            ! Field 9
        until: 05:00,                  ! Field 10
        15.6,                          ! Field 11
        until: 24:00,                  ! Field 12
        21;                            ! Field 13

    *** after
    Schedule:Compact,
        htgsetp_sch,                   ! Name
        temperature,                   ! Schedule Type Limits Name
        through: 12/31,                ! Field 0
        for: summerdesignday,          ! Field 1
        until: 24:00,                  ! Field 2
        15.6,                          ! Field 3
        for: winterdesignday,          ! Field 4
        until: 24:00,                  ! Field 5
        22.0,                          ! Field 6
        for: allotherdays,             ! Field 7
        until: 01:00,                  ! Field 8
        22.0,                          ! Field 9
        until: 05:00,                  ! Field 10
        15.6,                          ! Field 11
        until: 24:00,                  ! Field 12
        22.0;                          ! Field 13

    *** before
    Schedule:Compact,
        htgsetp_kitchen_sch,           ! Name
        temperature,                   ! Schedule Type Limits Name
        through: 12/31,                ! Field 0
        for: summerdesignday,          ! Field 1
        until: 24:00,                  ! Field 2
        15.6,                          ! Field 3
        for: winterdesignday,          ! Field 4
        until: 24:00,                  ! Field 5
        19,                            ! Field 6
        for: allotherdays,             ! Field 7
        until: 01:00,                  ! Field 8
        19,                            ! Field 9
        until: 05:00,                  ! Field 10
        15.6,                          ! Field 11
        until: 24:00,                  ! Field 12
        19;                            ! Field 13

    *** after
    Schedule:Compact,
        htgsetp_kitchen_sch,           ! Name
        temperature,                   ! Schedule Type Limits Name
        through: 12/31,                ! Field 0
        for: summerdesignday,          ! Field 1
        until: 24:00,                  ! Field 2
        15.6,                          ! Field 3
        for: winterdesignday,          ! Field 4
        until: 24:00,                  ! Field 5
        20.0,                          ! Field 6
        for: allotherdays,             ! Field 7
        until: 01:00,                  ! Field 8
        20.0,                          ! Field 9
        until: 05:00,                  ! Field 10
        15.6,                          ! Field 11
        until: 24:00,                  ! Field 12
        20.0;                          ! Field 13