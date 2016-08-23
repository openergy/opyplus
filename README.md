# oplus

## Installation

    pip install git+http://git@github.com/Openergy/oplus.git

## What is it
A python package for working with Energy Plus

## Releases

(p): patch, (m): minor, (M): major

### 4.3.0
* new cache system
* new configuration system
* CONF functions changed

### 4.4.0
* simulation api changed
* summary table object implemented
* err object implemented
* can create idf and epw from path, content or buffer
* can copy idf

### next
* **(p)simulation.py**:
    * debug: simulate failed to return Simulation object if simulation_name was not none. Corrected.
    * debug: osx summary table file name was wrong
* **(m) idf.py**: new filter condition added : 'in', debug of filter with no condition
