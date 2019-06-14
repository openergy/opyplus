# oplus

**M: major, m: minor, p: patch**

## 7.0.1.dev210
* m: save/load api implemented for epm and weather data

## 7.0.1.dev201
* p: create_datetime_instants debug

## 7.0.1.dev200
* M: energy+ version is now managed based on epm version. All idds are now stored in package, computers idd is not used anymore.
* M: new simulation interface
* M: new weather interface

## 7.0.1.dev110
* m: new check_length argument for epm 
* p: debug iter records while modifying primary key
* p: debug hook value modification

## 7.0.1.dev100
* M: standard output was refactored, api changed

## 7.0.1.dev010
* m: can load specific tables only while creating an epm

## 7.0.1.dev002
* p: external files system was modified/debuged
* p: weather data debug
* p: api fixes

## 7.0.1.dev001
* p: hook error messages debug
* M: new weather data management
* p: documentation is up to date
* M: all input and output objects have been modified

## 7.0.1.dev0
* WARNING: only epm chapter really works, and it is not thoroughly tested. Documentation is not up to date.
* M: new syntax
* m: links and hooks have been re-coded

## 6.1.1
* p: manage EplusDt no leap year

## 6.1.0
* p: debug ref field in record_manager

## 6.0.1.dev7
* p: removed plotly requirement

## 6.0.1.dev6
* p: ``oplus.idd.Idd.get_idd`` better error message

## 6.0.1.dev5
* p: debug ``oplus.idd.Idd.get_idd`` class method to admit instances inheriting
from oplus Idd instance instead of only admitting oplus Idd instances. 

## 6.0.1.dev4
* p: debug in idd.record_descriptor.get_field_index
* p: set_value debug if value is None

## 6.0.1.dev3
* p: idd now keeps tags with no values
* m: idd now has a record_descriptor_l property
* m: ``__eq__`` magic method implemented for FieldDescriptor, RecordDescriptor objects, and Idd
* m: ``RecordDescriptor.get_tag`` has now a ``raw`` kwarg in case
one would like the tag without preprocessing (i.e. concatenation of
``\memo`` tags)
* m: ``FieldDescriptor.get_tag`` has now a ``raw`` kwarg in case
one would like the tag without preprocessing (i.e. concatenation of
``\note`` tags)
* p: debug idd parsing to allow strings s.a. `N9, \note fields as indicated` 
to be parsed
* m: custom idd is enabled in simulation
* m: ``remove_tag`` method added in ``FieldDescriptor``
* m: can specify which .idd file to use in simulation
* p: ``idd_cls`` in IdfManager for subclassing
* p: Idd path becomes ``path_or_key``, through which the user can pass a key s.a.
"energy+" to default the .idd file to EnergyPlus one. This was created so users could
up-cast the Idd object and customize the different default .idd sources. 


## 6.0.1.dev2
* p: requirements are now specified in the requirements.txt file
* m: raise_if_pointed keyword argument reintroduced in `idf.remove`
* p: improved idf.under_construction decorator

## 6.0.1.dev1
* m: table class can now be subclassed
* m: record may now implement init_instance class method
* m: table now has an idf property 


## 6.0.1.dev0
*tested on Windows 10*
* p: __getitem__ added to table
* M: new syntax (idf/table/queryset/record with select and one)
* m: pointing/pointed records managed
* p: operating system management has been structured
* p: logging is improved
* p: big source code files have been split
* p: __str__, __repr__ and .info has been improved / simplified
* M: unused custom exceptions have been removed

## 5.1.2
* p: tests are now properly organized

## 5.1.1
* p: Fixed bug on the caching system for IDF objects

## 5.1.0
* m: Caching is now managed automatically
* m: Added the under_construction mode to add several objects in a more efficient manner

## 5.0.0
* p: debug architecture linux for 8.5.0 EnergyPlus version 
(Output directory no longer exists)
* m: EIO logger name argument
* M: EPWHeader, removed: start day of week, get field, set field
* m: EPW logger name
* p: sort_df to account for pandas backward compatibilities
* p: debug double space in eplusout.err strings
* p: in parsing *.err file, debug the case when "\******* Beginnning" is never encountered
* m: Idd loggers
* m: MTD logger name
* m: OutputTable logger name
* p: simulation debug read_only epw files when copied
* p: linux compatibility for EnergyPlus 8.6.0
* M: pandas sort_index instead of deprecated sort
* m: report_key management in SummaryTable.get_table_df
* p: redirect stream debug
* p: run_subprocess encoding

## 4.6.0
* m: idf styles added
* m: epw header completed
* p: err debug
* m: simulation beat_freq implemented
* p: subprocess management enhanced

## 4.5.1
* **p conda-requirements.txt added, setup.py enhanced**

## 4.5.0
* **psimulation.py**:
    * debug: simulate failed to return Simulation object if simulation_name was not none. Corrected.
    * debug: osx summary table file name was wrong
* **m idf.py**: new filter condition added : 'in', debug of filter with no condition

## 4.4.3
* corrected PyPi hosting issues

## 4.4.2
* implemented continuous integration

## 4.4.1
* simulation debug: simulate failed to return Simulation object if simulation_name was not none. Corrected.

## 4.4.0
* simulation api changed
* summary table object implemented
* err object implemented
* can create idf and epw from path, content or buffer
* can copy idf

## 4.3.0
* new cache system
* new configuration system
* CONF functions changed
