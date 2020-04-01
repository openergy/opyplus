Parametric simulations
======================

This example shows how to do a sensitivity study using opyplus.

Prepare imports and paths
-------------------------

.. testsetup::

    import os
    import tempfile
    initial_cwd = os.getcwd()
    temp_dir = tempfile.TemporaryDirectory()
    os.chdir(temp_dir.name)


.. testcode::

    import os
    import opyplus as op

    eplus_dir_path = op.get_eplus_base_dir_path((9, 0, 1))


Define input files
------------------

.. testcode::

    # idf (building model)
    base_idf_path = os.path.join(
        eplus_dir_path,
        "ExampleFiles",
        "RefBldgFullServiceRestaurantNew2004_Chicago.idf"
        )

    # epw (weather)
    epw_path = os.path.join(
        eplus_dir_path,
        "WeatherData",
        "USA_CO_Golden-NREL.724666_TMY3.epw"
        )



Define the study plan
----------------------


Variables and values
^^^^^^^^^^^^^^^^^^^^

.. testcode::

    sensitivity_plan = {
        "light" : [0.5, 1.5], # modify Lights value
        "electric_equipment" : [0.5, 1.5], # modify ElectricEquipment level
        "infiltration" : [0.5, 1.5], # modify ZoneInfiltration_DesignFlowRate level
        "business_days" : ["schedule_light", "schedule_heavy"], # change setpoint schedule
        "heating_setpoint" : [ -1, 1], # modify schedule's upper value
        }


Define the function that will modify the model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. testcode::

    def modify_model(epm, parameter, value):

        if parameter == "light":
            # modify light level
            for light in epm.Lights:
                light.watts_per_zone_floor_area *= value
            return

        if parameter == "electric_equipment":
            # modify electric level
            for ee in epm.ElectricEquipment:
                if ee.design_level_calculation_method == "equipmentlevel":
                    ee.design_level *= value
                elif ee.design_level_calculation_method == "watts/area":
                    ee.watts_per_zone_floor_area *= value
            return

        if parameter == "infiltration":
            # modify infiltration flow
            for inf in epm.ZoneInfiltration_DesignFlowRate:
                if inf.design_flow_rate_calculation_method == "flow/exteriorarea":
                    inf.flow_per_exterior_surface_area *= value
                elif inf.design_flow_rate_calculation_method == "airchanges/hour":
                    inf.air_changes_per_hour *= value
            return

        if parameter == "business_days":
            # change schedule value
            if value == "schedule_light":
                heating_setpoint_temperature_list = []
                for th_ds in epm.ThermostatSetpoint_DualSetpoint:
                    heating_setpoint_temperature_list.append(
                        th_ds.heating_setpoint_temperature_schedule_name)

                # loop and replace value
                for heating_setpoint_sch in set(heating_setpoint_temperature_list):
                    # clear values
                    heating_setpoint_sch.clear_extensible_fields()
                    # update
                    heating_setpoint_sch.update({
                        0: heating_setpoint_sch[0],
                        1: heating_setpoint_sch[1],
                        2: "through: 12/31",
                        3: "for monday tuesday thursday friday",
                        4: "until: 07:00",
                        5: "16",
                        4: "until: 18:00",
                        5: "21",
                        4: "until: 24:00",
                        5: "16",
                        6: "for allotherdays",
                        7: "until: 24:00",
                        8: "16",
                    })

            elif value == "schedule_heavy":
                heating_setpoint_temperature_list = []
                for th_ds in epm.ThermostatSetpoint_DualSetpoint:
                    heating_setpoint_temperature_list.append(
                    th_ds.heating_setpoint_temperature_schedule_name)

                # loop and replace value
                for heating_setpoint_sch in set(heating_setpoint_temperature_list):
                    # clear values
                    heating_setpoint_sch.clear_extensible_fields()
                    # update
                    heating_setpoint_sch.update({
                        0: heating_setpoint_sch[0],
                        1: heating_setpoint_sch[1],
                        2: "through: 12/31",
                        3: "for monday tuesday wednesday thursday friday saturday",
                        4: "until: 05:00",
                        5: "16",
                        4: "until: 21:00",
                        5: "21",
                        4: "until: 24:00",
                        5: "16",
                        6: "for allotherdays",
                        7: "until: 24:00",
                        8: "16",
                    })
            return

        if parameter == "heating_setpoint":
            heating_setpoint_temperature_list = []
            for th_ds in epm.ThermostatSetpoint_DualSetpoint:
                heating_setpoint_temperature_list.append(
                    th_ds.heating_setpoint_temperature_schedule_name
                    )

            # loop and replace value
            for heating_setpoint_sch in sorted(heating_setpoint_temperature_list):
                schedule_dict = heating_setpoint_sch.to_dict()
                first_index = max(
                    schedule_dict,
                    key=lambda x: float(schedule_dict[x])
                        if isinstance(schedule_dict[x], str) and schedule_dict[x].isdigit()
                        else 0
                )
                for k, v in schedule_dict.items():
                    if v == schedule_dict[first_index]:
                        heating_setpoint_sch[k] = str(float(schedule_dict[k]) + value)

            return

        raise ValueError(f"unknown parameter: {parameter}")


Create the function that will run the simulation and prepare outputs
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this example we will add specific output variables to the model, simulate and return consumptions.

.. testcode::


    def simulate_and_get_result(epm, epw_path, simulation_name):
        # add output variables
        epm.output_variable.add({
            0: "*",
            1: "Zone Air Terminal Sensible Heating Energy",
            2: "hourly"
        })
        epm.output_variable.add({
            0: "*",
            1: "Zone Air Terminal Sensible Cooling Energy",
            2: "hourly"
        })

        # simulate
        s = op.simulate(epm, epw_path, simulation_name)

        # get results
        eso = s.get_out_eso()
        eso.create_datetime_index(2020)
        hourly_df = eso.get_data()

        # filter and aggregate outputs
        regex_sensible = "Zone Air Terminal Sensible"
        regex_electric = "electricity:facility"
        sensible_baseline = hourly_df.filter(regex=regex_sensible).sum(axis=1).sum()
        electric_baseline = hourly_df.filter(regex=regex_electric).sum(axis=1).sum()

        # return baselines
        return sensible_baseline, electric_baseline


Run the study
-------------

.. testcode::

    # calculate baseline
    epm = op.Epm.load(base_idf_path)
    electric_baseline, sensible_baseline = simulate_and_get_result(
        epm,
        epw_path,
        "baseline"
    )

    # run sensitivity study
    results = dict()  # {simulation_name: {"electric": , "sensible": }
    for parameter, values in sensitivity_plan.items():
        for value in values:
            # reload initial model
            epm = op.Epm.load(base_idf_path)

            # modify model
            modify_model(epm, parameter, value)

            # simulate and calculate outputs
            sensible_consumption, electric_consumption = simulate_and_get_result(
                epm,
                epw_path,
                f"{parameter}-{str(value)}"  # simulation name
            )

            # store results
            results[simulation_name] = dict(
                electric=(electric_consumption-electric_baseline)/electric_baseline,
                sensible=(sensible_consumption-sensible_baseline)/sensible_baseline
            )

            # store results
            results[simulation_name] = dict(
                electric=(electric_consumption-electric_baseline)/electric_baseline,
                sensible=(sensible_consumption-sensible_baseline)/sensible_baseline
            )

Visualize the results
---------------------

We use the plotly package to visualize the results.

Imports
^^^^^^^

.. testcode::

    import plotly.graph_objs as go
    import pandas as pd

Plot
^^^^

.. testcode::

    df = pd.DataFrame().from_dict(results).T

    fig = go.Figure(
        data=[go.Bar(
            x=df.index, y=df["sensible"]
        )],
        layout=go.Layout(title="Zone Air Terminal Sensible Energy (%)")
    )

    fig.show()

.. figure:: logo-dark.png
    :scale: 80 %
    :alt: Openergy logo
    :align: center

    Openergy's logo

.. testcode::

    fig = go.Figure(
        data=[go.Bar(
            x=df.index, y=df["electric"]
        )],
        layout=go.Layout(title="electricity:facility (%)")
    )

    fig.show()

.. testcleanup::

    # come back to initial cwd
    os.chdir(initial_cwd)
