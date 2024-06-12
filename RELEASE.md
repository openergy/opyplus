# Changelog

    M: major
    m: minor
    p: patch

## next
* m: officially supports python >=3.8,<3.13
* m: drop python 3.7 support 

## 1.6.1
* p: reconnected to pypi account

## 1.6.0
* m: implementing DesignDay model from ddy  
* p: fix latest default idd version in conf
* p: code refactoring to create parent model Epgm
* p: devops debug, initiating azure pipelines to github actions migration
* p: tests implemented on EnergyPlus 22.1.0 (ubuntu os, only)

## 1.5.0
* p: documentation generation debug
* m: idd 22.2.0, idd 23.1.0, idd 23.2.0 were added

## 1.4.2
* p: preserve order of ``EnergyManagementSystem:ProgramCallingManager`` objects when saving
``Epm``.
* p: handle 0-length records

## 1.4.1
* p: simulation run if file path contains space now works

## 1.4.0
* m: idd 22.1.0 was added

## 1.3.0
* m: idd 9.6.0 was added

## 1.2.1
* p: subprocess.Popen is now run with shell=True 

## 1.2.0
* m: idd 9.4.0 and 9.5.0 added

## 1.1.3
* p: idd group recognition debug

## 1.1.2
* p: fix version number issue

## 1.1.1
* p: compatibility with pandas 1.1.0

## 1.1.0
* p: unnecessary files where removed
* m: record slice was implemented
* p: table_multivariablelookup idd_debug.py debug

## 1.0.3
* p: first version of documentation is ready

## 1.0.2
* p: improve printing when parsing output (every 30 seconds instead of 60, and was missing in the second loop)
* p: improve output parsing memory and time efficiency by storing data in lists instead of dicts

## 1.0.1
* p: use pandas.testing instead of deprecated pandas.util.testing

## 1.0.0
* p: debug problems with weather data string columns (present_weather_codes)
* p: support pandas 1.0

## 1.0.0.dev6
* p: add parametric simulation examples
* p: improved documentation
* p: added docstring to all public function/module/class

## 1.0.0.dev5
* p: project added to readthedocs

## 1.0.0.dev4
* M: changed name to opyplus, prepare to publish
