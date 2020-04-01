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
            5: "16",
            4: "until: 19:00",
            5: "21",
            4: "until: 24:00",
            5: "16",
        })

expert example - find upper value and modify it

.. testcode::

    ## get all heating setpoint for ThermostatSetpoint:DualSetpoint object
    heating_setpoint_temperature_list = []
    for th_ds in epm.ThermostatSetpoint_DualSetpoint:
        heating_setpoint_temperature_list.append(th_ds.heating_setpoint_temperature_schedule_name)
    ## loop on
    for hsch in sorted(heating_setpoint_temperature_list):
        print("*** before")
        print(hsch)
        schedule_dict = hsch.to_dict()
        first_index = max(schedule_dict, key=lambda key: float(schedule_dict[key]) if isinstance(schedule_dict[key], str) and schedule_dict[key].isdigit() else 0)
        for i,v in schedule_dict.items():
            if v == schedule_dict[first_index]:
                hsch[i] = str(float(schedule_dict[i]) + 1)
        print("*** after")
        print(hsch)

.. testoutput::
   :options: +NORMALIZE_WHITESPACE

   *** before
    Schedule:Compact,
        htgsetp_kitchen_sch,           ! Name
        temperature,                   ! Schedule Type Limits Name
        through: 12/31,                ! Field 1
        for alldays,                   ! Field 2
        until: 24:00,                  ! Field 3
        16,                            ! Field 4
        for: winterdesignday,          ! Field 5
        until: 24:00,                  ! Field 6
        19,                            ! Field 7
        for: allotherdays,             ! Field 8
        until: 01:00,                  ! Field 9
        19,                            ! Field 10
        until: 05:00,                  ! Field 11
        15.6,                          ! Field 12
        until: 24:00,                  ! Field 13
        19;                            ! Field 14
    *** after
    Schedule:Compact,
        htgsetp_kitchen_sch,           ! Name
        temperature,                   ! Schedule Type Limits Name
        through: 12/31,                ! Field 1
        for alldays,                   ! Field 2
        until: 24:00,                  ! Field 3
        16,                            ! Field 4
        for: winterdesignday,          ! Field 5
        until: 24:00,                  ! Field 6
        20.0,                          ! Field 7
        for: allotherdays,             ! Field 8
        until: 01:00,                  ! Field 9
        20.0,                          ! Field 10
        until: 05:00,                  ! Field 11
        15.6,                          ! Field 12
        until: 24:00,                  ! Field 13
        20.0;                          ! Field 14
    *** before
    Schedule:Compact,
        htgsetp_sch,                   ! Name
        temperature,                   ! Schedule Type Limits Name
        through: 12/31,                ! Field 1
        for alldays,                   ! Field 2
        until: 24:00,                  ! Field 3
        16,                            ! Field 4
        for: winterdesignday,          ! Field 5
        until: 24:00,                  ! Field 6
        21,                            ! Field 7
        for: allotherdays,             ! Field 8
        until: 01:00,                  ! Field 9
        21,                            ! Field 10
        until: 05:00,                  ! Field 11
        15.6,                          ! Field 12
        until: 24:00,                  ! Field 13
        21;                            ! Field 14
    *** after
    Schedule:Compact,
        htgsetp_sch,                   ! Name
        temperature,                   ! Schedule Type Limits Name
        through: 12/31,                ! Field 1
        for alldays,                   ! Field 2
        until: 24:00,                  ! Field 3
        16,                            ! Field 4
        for: winterdesignday,          ! Field 5
        until: 24:00,                  ! Field 6
        22.0,                          ! Field 7
        for: allotherdays,             ! Field 8
        until: 01:00,                  ! Field 9
        22.0,                          ! Field 10
        until: 05:00,                  ! Field 11
        15.6,                          ! Field 12
        until: 24:00,                  ! Field 13
        22.0;                          ! Field 14
