Parametric simulations
======================

This example shows how to do a sensibility study using opyplus.

Imports
-------

.. testcode::

    import tempfile
    temp_dir = tempfile.TemporaryDirectory()
    work_dir_path = temp_dir.name
    import os
    import opyplus as op

Define your Files
-----------------

.. testcode::

    # select epw
    example_epw_path = os.path.join(
        op.get_eplus_base_dir_path((9, 0, 1)),
        "WeatherData",
        "USA_CO_Golden-NREL.724666_TMY3.epw"
        )
    # select idf
    example_idf_path = os.path.join(
        op.get_eplus_base_dir_path((9, 0, 1)),
        "ExampleFiles",
        "RefBldgFullServiceRestaurantNew2004_Chicago.idf"
        )


Define your Study Plan
----------------------

.. testcode::

    sensibility_plan = {
        "light" : [0.5, 1.5], # we will modify level value for Lights object
        "electric_equipment" : [0.5, 1.5], # we will modify level value for ElectricEquipment object
        "infiltration" : [0.5, 1.5], # we will modify level value for ZoneInfiltration_DesignFlowRate object
        "business_days" : ["schedule_light", "schedule_heavy"], # we will change setpoint schedule
        "heating_setpoint" : [ -1, 1], # we will modify upper schedule value
        }


Create a function modifying your model
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

We define a function modifying the EnergyPlus model according the study input parameters

.. testcode::

    def modify_model(epm, parameter, value):

        if parameter == "light":
            ### modify light level
            for light in epm.Lights:
                light.watts_per_zone_floor_area *= value

        elif parameter == "electric_equipment":
            ### modify electric level
            for ee in epm.ElectricEquipment:
                if inf.design_flow_rate_calculation_method == "equipmentlevel":
                    ee.design_level *= value
                elif ee.design_level_calculation_method == "watts/area":
                    ee.watts_per_zone_floor_area *= value

        elif parameter == "infiltration":
            ### modify infiltration flow
            for inf in epm.ZoneInfiltration_DesignFlowRate:
                if inf.design_flow_rate_calculation_method == "flow/exteriorarea":
                    inf.flow_per_exterior_surface_area *= value
                elif inf.design_flow_rate_calculation_method == "airchanges/hour":
                    inf.air_changes_per_hour *= value

        elif parameter == "business_days":
            ### change schedule value
            if value == "schedule_light":
                heating_setpoint_temperature_list = []
                for th_ds in epm.ThermostatSetpoint_DualSetpoint:
                    heating_setpoint_temperature_list.append(th_ds.heating_setpoint_temperature_schedule_name)
                #### loop on and replace value
                for hsch in set(heating_setpoint_temperature_list):
                    hsch.update({
                        0: hsch[0],
                        1: hsch[1],
                        2: "through: 12/31",
                        3: "for monday tuesday thursday friday, ",
                        4: "until: 07:00",
                        5: "16",
                        4: "until: 18:00",
                        5: "21",
                        4: "until: 24:00",
                        5: "16",
                        6: "for alldays",
                        7: "until: 24:00",
                        8: "16",
                    })

            elif value == "schedule_heavy":
                heating_setpoint_temperature_list = []
                for th_ds in epm.ThermostatSetpoint_DualSetpoint:
                    heating_setpoint_temperature_list.append(th_ds.heating_setpoint_temperature_schedule_name)
                #### loop on and replace value
                for hsch in set(heating_setpoint_temperature_list):
                    hsch.update({
                        0: hsch[0],
                        1: hsch[1],
                        2: "through: 12/31",
                        3: "for monday tuesday wednesday thursday friday saturday,",
                        4: "until: 05:00",
                        5: "16",
                        4: "until: 21:00",
                        5: "21",
                        4: "until: 24:00",
                        5: "16",
                        6: "for alldays",
                        7: "until: 24:00",
                        8: "16",
                    })

        elif parameter == "heating_setpoint":
            ### change upper schedule value
            heating_setpoint_temperature_list = []
            for th_ds in epm.ThermostatSetpoint_DualSetpoint:
                heating_setpoint_temperature_list.append(th_ds.heating_setpoint_temperature_schedule_name)
            ### loop on
            for hsch in sorted(heating_setpoint_temperature_list):
                schedule_dict = hsch.to_dict()
                first_index = max(schedule_dict, key=lambda key: float(schedule_dict[key]) if isinstance(schedule_dict[key], str) and schedule_dict[key].isdigit() else 0)
                for i,v in schedule_dict.items():
                    if v == schedule_dict[first_index]:
                        hsch[i] = str(float(schedule_dict[i]) + value)


Create a function to run your model and select the study result
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In this example we will add specific output variables to the model, simulate and return consumptions

.. testcode::


    def simulate_and_get_result(epm, example_epw_path, simulation_path_name):

        ## add output variable
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

        name = "baseline"
        ## simulate
        s = op.simulate(epm, example_epw_path, simulation_path_name)
        ## get result
        eso = s.get_out_eso()
        eso.create_datetime_index(2020)
        hourly_df = eso.get_data()

        regex_sensible = "Zone Air Terminal Sensible"
        regex_electric = "electricity:facility"
        baseline_sensible = hourly_df.filter(regex=regex_sensible).sum(axis=1).sum()
        baseline_electric = hourly_df.filter(regex=regex_electric).sum(axis=1).sum()
        return baseline_sensible,baseline_electric


Run your study
--------------

.. testcode::

    result_d = {}
    for parameter in sensibility_plan.keys():
        for value in sensibility_plan[k]:

            epm = op.Epm.load(example_idf_path)

            modify_model(epm, parameter, value)

            simulation_path_name = f"{parameter}-{str(value)}"

            conso_sensible, conso_electric = simulate_and_get_result(epm, example_epw_path, simulation_path_name)

            result_d[name] = {}
            result_d[name]["Electric"] = (conso_electric-baseline_electric)/baseline_electric
            result_d[name]["Sensible"] = (conso_sensible-baseline_sensible)/baseline_sensible

Visualize the result
--------------------

We use the plotly package to visualize the results.

Imports
^^^^^^^

.. testcode::

    from plotly.offline import plot, iplot, init_notebook_mode
    import plotly.graph_objs as go
    init_notebook_mode()
    import pandas as pd

Plot
^^^^

.. testcode::

    df = pd.DataFrame().from_dict(result_d).T

    fig = go.Figure(
        data=[go.Bar(
            x=df.index, y=df['Sensible']
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
            x=df.index, y=df['Electric']
        )],
        layout=go.Layout(title="electricity:facility (%)")
    )

    fig.show()