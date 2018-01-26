# oplus

**(M): major, (m): minor, (p): patch**

## Next
* (m): EIO logger name argument
* (M): EPWHeader, removed:
    - start day of week
    - get field
    - set field
* (m): EPW logger name
* (p): sort_df to account for pandas backward compatibilities
* (p): debug double space in eplusout.err strings
* (p): in parsing *.err file, debug the case when "\******* Beginnning" is
never encountered
* (m): IDD loggers
* (m): MTD logger name
* (m): OutputTable logger name
* (p): simulation debug read_only epw files when copied
* (p): linux compatibility for EnergyPlus 8.6.0
* (M): pandas sort_index instead of deprecated sort
* (m): report_key management in SummaryTable.get_table_df
* (p): redirect stream debug
* (p): run_subprocess encoding

## 4.6.0

