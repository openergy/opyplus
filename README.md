# oplus

## Installation

    pip install git+http://git@github.com/Openergy/oplus.git

## What is it
A python package for working with Energy Plus

## Releases

*(M): major, (m): minor, (p): patch*

### 4.5.1
* **(p) conda-requirements.txt added, setup.py enhanced**

### 4.5.0
* **(p)simulation.py**:
    * debug: simulate failed to return Simulation object if simulation_name was not none. Corrected.
    * debug: osx summary table file name was wrong
* **(m) idf.py**: new filter condition added : 'in', debug of filter with no condition

### 4.4.3
* corrected PyPi hosting issues

### 4.4.2
* implemented continuous integration

### 4.4.1
* simulation debug: simulate failed to return Simulation object if simulation_name was not none. Corrected.

### 4.4.0
* simulation api changed
* summary table object implemented
* err object implemented
* can create idf and epw from path, content or buffer
* can copy idf

### 4.3.0
* new cache system
* new configuration system
* CONF functions changed
