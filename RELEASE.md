# Changelog

    M: major
    m: minor
    p: patch
    
## next
* p: extensible fields debug: cycle now starts at 1 and not 0 (print(record) displayed a cycle starting at 0, and using 
field name with cycle 0 returned a field before extensible cycle)

## next
* p: documentation was enhanced

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
