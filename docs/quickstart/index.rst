Quickstart
==========


Installation
^^^^^^^^^^^^

opyplus can be installed using conda or pip:

.. code-block:: bash

    pip install opyplus

.. code-block:: bash

    conda install -c conda-forge opyplus

Simulation
^^^^^^^^^^

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

    eplus_dir_path = op.get_eplus_base_dir_path((9, 0, 1))

Prepare input paths and run simulation.

.. testcode::

    # idf path
    idf_path = os.path.join(
        eplus_dir_path,
        "ExampleFiles",
        "1ZoneEvapCooler.idf"
    )

    # epw path
    epw_path = os.path.join(
        eplus_dir_path,
        "WeatherData",
        "USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"
    )

    # run simulation
    s = op.simulate(idf_path, epw_path, "my-first-simulation")

Check status, and inspect EPlus .err file.

.. testcode::

    print(f"status: {s.get_status()}\n")
    print(f"Eplus .err file:\n{s.get_out_err().get_content()}")

.. testoutput::
    :options: +SKIP

    status: finished

    Eplus .err file:
    Program Version,EnergyPlus, Version 9.0.1-bb7ca4f0da, YMD=2020.02.26 14:05,
       ** Warning ** Weather file location will be used rather than entered (IDF) Location object.
       **   ~~~   ** ..Location object=DENVER CENTENNIAL CO USA WMO=724666
       **   ~~~   ** ..Weather File Location=San Francisco Intl Ap CA USA TMY3 WMO#=724940
       **   ~~~   ** ..due to location differences, Latitude difference=[2.12] degrees, Longitude difference=[17.22] degrees.
       **   ~~~   ** ..Time Zone difference=[1.0] hour(s), Elevation difference=[99.89] percent, [1791.00] meters.
       ** Warning ** SetUpDesignDay: Entered DesignDay Barometric Pressure=81560 differs by more than 10% from Standard Barometric Pressure=101301.
       **   ~~~   ** ...occurs in DesignDay=DENVER CENTENNIAL ANN HTG 99.6% CONDNS DB, Standard Pressure (based on elevation) will be used.
       ** Warning ** GetAirPathData: AirLoopHVAC="EVAP COOLER SYSTEM" has no Controllers.
       ** Warning ** SetUpDesignDay: Entered DesignDay Barometric Pressure=81560 differs by more than 10% from Standard Barometric Pressure=101301.
       **   ~~~   ** ...occurs in DesignDay=DENVER CENTENNIAL ANN CLG 1% CONDNS DB=>MWB, Standard Pressure (based on elevation) will be used.
       ************* Testing Individual Branch Integrity
       ************* All Branches passed integrity testing
       ************* Testing Individual Supply Air Path Integrity
       ************* All Supply Air Paths passed integrity testing
       ************* Testing Individual Return Air Path Integrity
       ************* All Return Air Paths passed integrity testing
       ************* No node connection errors were found.
       ************* Beginning Simulation
       ************* Simulation Error Summary *************
       ************* EnergyPlus Warmup Error Summary. During Warmup: 0 Warning; 0 Severe Errors.
       ************* EnergyPlus Sizing Error Summary. During Sizing: 0 Warning; 0 Severe Errors.
       ************* EnergyPlus Completed Successfully-- 4 Warning; 0 Severe Errors; Elapsed Time=00hr 00min  7.05sec

Retrieve and display outputs.

.. testcode::

    # retrieve hourly output (.eso file)
    hourly_output = s.get_out_eso()

    # ask for datetime index on year 2013
    hourly_output.create_datetime_index(2013)

    # get Pandas dataframe
    df = hourly_output.get_data()

    # monthly resample and display
    print(df[[
        "environment,Site Outdoor Air Drybulb Temperature",
        "main zone,Zone Mean Air Temperature"
    ]].resample("MS").mean())

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

                environment,Site Outdoor Air Drybulb Temperature  main zone,Zone Mean Air Temperature
    2013-01-01                                          9.598712                            20.009400
    2013-02-01                                         11.289435                            20.154321
    2013-03-01                                         12.659767                            20.354625
    2013-04-01                                         13.678194                            20.515966
    2013-05-01                                         15.002352                            20.661471
    2013-06-01                                         15.336250                            21.001910
    2013-07-01                                         15.936470                            20.998396
    2013-08-01                                         16.618201                            21.260456
    2013-09-01                                         16.718843                            21.171012
    2013-10-01                                         15.105724                            20.569441
    2013-11-01                                         12.785648                            20.182358
    2013-12-01                                         10.658524                            20.026346


EPlus Model (idf file)
^^^^^^^^^^^^^^^^^^^^^^

Load Energy Plus model.

.. testcode::

    # idf path
    idf_path = os.path.join(
        eplus_dir_path,
        "ExampleFiles",
        "1ZoneEvapCooler.idf"
    )

    # load epm object
    epm = op.Epm.from_idf(idf_path)


Iter constructions:

.. testcode::

    for construction in epm.Construction:
        print(construction)

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Construction,
        r13wall,                       ! Name
        r13layer;                      ! Outside Layer
    Construction,
        floor,                         ! Name
        c5 - 4 in hw concrete;         ! Outside Layer
    Construction,
        roof31,                        ! Name
        r31layer;                      ! Outside Layer


Retrieve concrete material.

.. testcode::

    concrete = epm.Material.one("c5 - 4 in hw concrete")
    print(concrete)


.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Material,
        c5 - 4 in hw concrete,         ! Name
        mediumrough,                   ! Roughness
        0.1014984,                     ! Thickness
        1.729577,                      ! Conductivity
        2242.585,                      ! Density
        836.8,                         ! Specific Heat
        0.9,                           ! Thermal Absorptance
        0.65,                          ! Solar Absorptance
        0.65;                          ! Visible Absorptance


Change thickness and conductivity.

.. testcode::

    # change thickness and conductivity
    concrete.thickness = 0.2
    concrete.conductivity = 1.5

    # print new values
    print(concrete)

    # save new idf
    epm.save("my-first-model.idf")

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Material,
        c5 - 4 in hw concrete,         ! Name
        mediumrough,                   ! Roughness
        0.2,                           ! Thickness
        1.5,                           ! Conductivity
        2242.585,                      ! Density
        836.8,                         ! Specific Heat
        0.9,                           ! Thermal Absorptance
        0.65,                          ! Solar Absorptance
        0.65;                          ! Visible Absorptance


Outputs (eso file)
^^^^^^^^^^^^^^^^^^

Connect to previous simulation and retrieve eso object.

.. testcode::

    s = op.Simulation("my-first-simulation")
    eso = s.get_out_eso()

Display what is contained in eso file (environments, variable names and frequencies).

.. testcode::

    print(eso.get_info())

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    Standard output
      environments
        denver centennial ann htg 99.6% condns db (0)
          latitude: 37.62
          longitude: -122.4
          timezone_offset: -8.0
          elevation: 2.0
        denver centennial ann clg 1% condns db=>mwb (1)
          latitude: 37.62
          longitude: -122.4
          timezone_offset: -8.0
          elevation: 2.0
        runperiod 1 (2)
          latitude: 37.62
          longitude: -122.4
          timezone_offset: -8.0
          elevation: 2.0
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

Natively, outputs don't have a year and their indexes are not stored in datetimes (but in tuples of integers instead: month, day, hour).
We transform outputs to datetime index dataframes to ease future analysis (datetimes are easy to manipulate, for example for resample operations).

.. testcode::

    eso.create_datetime_index(2013)  # we indicate the year

Explore window design day data : display mean daily exterior and interior temperatures.

.. testcode::

    winter_design_day_df = eso.get_data("denver centennial ann htg 99.6% condns db")
    print(winter_design_day_df[[
        "main zone,Zone Mean Air Temperature",
        "environment,Site Outdoor Air Drybulb Temperature"
        ]].resample("D").mean()
    )

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

                main zone,Zone Mean Air Temperature  environment,Site Outdoor Air Drybulb Temperature
    2013-12-21                                 20.0                                             -18.8

Explore run period data : display mean daily exterior and interior temperatures.

.. testcode::

    # default environment is the last one found, which is the run period environment in our case
    run_period_df = eso.get_data()

    # daily resample
    daily_df = run_period_df[[
        "main zone,Zone Mean Air Temperature",
        "environment,Site Outdoor Air Drybulb Temperature"
        ]].resample("D").mean()

    # display
    print(daily_df.head())  # will only display first rows of dataframe

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

                main zone,Zone Mean Air Temperature  environment,Site Outdoor Air Drybulb Temperature
    2013-01-01                            20.058282                                          8.704167
    2013-01-02                            20.035461                                          9.857639
    2013-01-03                            20.085657                                         12.200000
    2013-01-04                            20.000013                                          8.456250
    2013-01-05                            20.000000                                          7.819097

Export data in csv format.

.. testcode::

    eso.to_csv("ouputs-csv")

    # all csv files (one per environment and frequency) where created in one directory
    for name in sorted(os.listdir("ouputs-csv")):
        print(name)

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    0#denver-centennial-ann-htg-99-6-condns-db#hourly.csv
    1#denver-centennial-ann-clg-1-condns-db-mwb#hourly.csv
    2#runperiod-1#hourly.csv

Weather data (epw file)
^^^^^^^^^^^^^^^^^^^^^^^

Load Weather data.

.. testcode::

    # epw path
    epw_path = os.path.join(
        eplus_dir_path,
        "WeatherData",
        "USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw"
    )

    # load weather data object
    weather_data = op.WeatherData.from_epw(epw_path)


View synthetic info.

.. testcode::

    print(weather_data.get_info())


.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    WeatherData
        has datetime instants: False
        latitude: 37.62
        longitude: -122.40
        timezone_offset: -8.0
        elevation: 2.0
        data period: 1999-01-01T00:00:00, 1997-12-31T23:00:00



Natively, weather data index is not stored in datetimes (but in tuples of integers instead: year, month, day, hour).
We transform data to datetime index dataframe to ease future analysis (datetimes are easy to manipulate, for example for resample operations).

.. testcode::

    weather_data.create_datetime_instants(2013)  # we indicate start year

    # check that operation worked
    print(f"has datetime index: {weather_data.has_datetime_instants}")

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    has datetime index: True

Retrieve weather series data (pandas dataframe object).

.. testcode::

    df = weather_data.get_weather_series()

    # print columns
    print(f"columns: {list(sorted(df.columns))}\n")

    # print drybulb first rows
    print("drybulb:")
    print(df["drybulb"].head())

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    columns: ['Albedo', 'aerosol_opt_depth', 'atmos_pressure', 'ceiling_hgt', 'datasource', 'day', 'days_last_snow', 'dewpoint', 'difhorillum', 'difhorrad', 'dirnorillum', 'dirnorrad', 'drybulb', 'extdirrad', 'exthorrad', 'glohorillum', 'glohorrad', 'horirsky', 'hour', 'liq_precip_depth', 'liq_precip_rate', 'minute', 'month', 'opaqskycvr', 'precip_wtr', 'presweathcodes', 'presweathobs', 'relhum', 'snowdepth', 'totskycvr', 'visibility', 'winddir', 'windspd', 'year', 'zenlum']

    drybulb:
    2013-01-01 01:00:00    7.2
    2013-01-01 02:00:00    7.2
    2013-01-01 03:00:00    6.7
    2013-01-01 04:00:00    6.1
    2013-01-01 05:00:00    4.4
    Freq: H, Name: drybulb, dtype: float64

Add one degree celcius to drybulb and set new weather series.

.. testcode::

    # add one degree
    df["drybulb"] += 1  # equivalent of df["drybulb"] = df["drybulb"] + 1

    # set new dataframe
    weather_data.set_weather_series(df)

    # check it worked
    print(weather_data.get_weather_series()["drybulb"].head())

.. testoutput::
    :options: +NORMALIZE_WHITESPACE

    2013-01-01 01:00:00    8.2
    2013-01-01 02:00:00    8.2
    2013-01-01 03:00:00    7.7
    2013-01-01 04:00:00    7.1
    2013-01-01 05:00:00    5.4
    Freq: H, Name: drybulb, dtype: float64

Save data in a new epw file.

.. testcode::

    # save new epw
    weather_data.to_epw("one-more-drybulb-degree.epw")

.. testcleanup::

    # come back to initial cwd
    os.chdir(initial_cwd)

