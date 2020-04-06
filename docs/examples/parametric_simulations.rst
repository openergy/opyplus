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

    import opyplus as op
    current_doc_path = os.path.normpath(os.path.join(op.__file__, "..", "..", "docs", "examples"))


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
        "heating_setpoint" : [ -1, 1], # modify schedule's upper value
        "cooling_setpoint" : [ -1, 1], # modify schedule's lower value
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

        if parameter == "heating_setpoint":
            ## create a list with all heating setpoint temperature schedules found in ThermostatSetpoint_DualSetpoint objects
            heating_setpoint_temperature_list = []
            for th_ds in epm.ThermostatSetpoint_DualSetpoint: ### loop on ThermostatSetpoint_DualSetpoint object
                heating_setpoint_temperature_list.append(
                    th_ds.heating_setpoint_temperature_schedule_name) ### add heating_setpoint_temperature_schedule_name to list

            # loop on each heating_setpoint_temperature_schedule and replace value
            for heating_setpoint_sch in sorted(heating_setpoint_temperature_list):
                ## get dict of the schedule { 0: schedule'name, 1: schedule type limits name, 2: extensible field 1 value, ... }
                schedule_dict = heating_setpoint_sch.to_dict()
                ## get the index of max value
                first_index = max(
                    schedule_dict,
                    key=lambda x: float(schedule_dict[x])
                        if isinstance(schedule_dict[x], str) and schedule_dict[x].isdigit()
                        else 0 ### transform string to float if the value is a string and a can is a digit not a text
                )
                ## loop on all dict items and modify value if its the max value
                for k, v in schedule_dict.items():
                    if v == schedule_dict[first_index]: ### it is the max value ?
                        heating_setpoint_sch[k] = str(float(schedule_dict[k]) + value) ### update value and set it in string format

            return

        if parameter == "cooling_setpoint":
            ## create a list with all cooling setpoint temperature schedules found in ThermostatSetpoint_DualSetpoint objects
            cooling_setpoint_temperature_list = []
            for th_ds in epm.ThermostatSetpoint_DualSetpoint: ### loop on ThermostatSetpoint_DualSetpoint object
                cooling_setpoint_temperature_list.append(
                    th_ds.cooling_setpoint_temperature_schedule_name) ### add cooling_setpoint_temperature_schedule_name to list

            # loop on each cooling_setpoint_temperature_schedule and replace value
            for cooling_setpoint_sch in set(cooling_setpoint_temperature_list):
                ## get dict of the schedule { 0: schedule'name, 1: schedule type limits name, 2: extensible field 1 value, ... }
                schedule_dict = cooling_setpoint_sch.to_dict()
                ## get the index of max value
                first_index = min(
                    schedule_dict,
                    key=lambda x: float(schedule_dict[x])
                        if isinstance(schedule_dict[x], str) and schedule_dict[x].isdigit()
                        else 100 ### transform string to float if the value is a string and a can is a digit not a text
                )
                ## loop on all dict items and modify value if its the min value
                for k, v in schedule_dict.items():
                    if v == schedule_dict[first_index]: ### it is the min value ?
                        cooling_setpoint_sch[k] = str(float(schedule_dict[k]) + value) ### update value and set it in string format

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
        regex_gas = "gas:facility"
        sensible = hourly_df.filter(regex=regex_sensible).sum(axis=1).sum()
        electric = hourly_df.filter(regex=regex_electric).sum(axis=1).sum()
        gas = hourly_df.filter(regex=regex_gas).sum(axis=1).sum()

        # return baselines
        return sensible, electric+gas


Run the study
-------------

.. testcode::

    # calculate baseline
    epm = op.Epm.load(base_idf_path)
    sensible_need_baseline, total_consumption_baseline = simulate_and_get_result(
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

            # prepare simulation name
            simulation_name = f"{parameter}={str(value)}"

            # modify model
            modify_model(epm, parameter, value)

            # simulate and calculate outputs
            sensible_need, total_consumption = simulate_and_get_result(
                epm,
                epw_path,
                simulation_name
            )

            # store results
            results[simulation_name] = dict(
                total=(total_consumption-total_consumption_baseline)/total_consumption_baseline,
                sensible=(sensible_need-sensible_need_baseline)/sensible_need_baseline
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

    df.sort_values(by=["sensible"], inplace=True)

    sensible_fig = go.Figure(
        data=[go.Bar(
            x=df.index, y=df["sensible"]
        )],
        layout=go.Layout(title=
        """Relative error of each sensible plan simulation with the baseline for output: 'Zone Air Terminal Sensible Energy'""",
        font=dict(size=11,)
        )
    )

    sensible_fig.show()

.. raw:: html
    :file: sensible.html

This building model is more sensible to heating setpoint than other parameters.

.. testcode::

    df.sort_values(by=["electric"], inplace=True)

    cross_dependancy_fig = go.Figure(
        data=[go.Scatter(
            x=df["sensible"], y=df["total"], mode="markers", text=df.index
        )],
        layout=go.Layout(
            title="Dependancy correlation between consumption and sensible need",
            font=dict(size=11,),
            xaxis=dict(
              title="relative sensibility on air sensible energy",
            ),
            yaxis=dict(
                title= "relative sensibility on total consumption facility",
            )
        ),

    )

    cross_dependancy_fig.show()


.. raw:: html
    :file: cross_dependancy.html


We remark a good sensibility symmetry and a factor 3 between sensibility need and consumption.

.. testcleanup::

    # create plotly figures html
    sensible_fig.write_html(os.path.join(current_doc_path, "sensible.html"))
    electricity_fig.write_html(os.path.join(current_doc_path, "electricity.html"))

    # come back to initial cwd
    os.chdir(initial_cwd)
