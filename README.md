# oplus

A python package wrapper of Energy Plus.

## Documentation
* For users: see doc-users.md (use odocgen to improve)
* For developers: see doc-developers.md

## Tests

### Energy plus versions

Oplus is supposed to work with multiple versions of Energy Plus.
Currently, it is tested with the following versions (listed in TESTED_EPLUS_VERSIONS : oplus.tests.util):
* 8.5.0
* 8.6.0

Each test is therefore run multiple times : once per tested version. To automatically run a test on all versions, use
eplus_tester function (oplus.tests.util).

### Operating system

Oplus is supposed to work on multiple operating systems. The tested operating systems must be exposed in the RELEASE
file. For versions with no OS specified, the only covered os is the continuous integration server os (Ubuntu 16.04).

### Simulations

In order to limit the testing time, we limit the number of simulations performed during tests : only one test performs 
a simulation (one simulation per eplus version). This simulation must be as quick as possible.

When testing objects that manipulate simulation outputs, simulation must be performed once by the developer, and it's
outputs are saved in the source code. In order to keep the repo size low, we try as much as possible to mutualize
tested outputs, and we limit it's size (limit simulation timestep, time range, ...).
