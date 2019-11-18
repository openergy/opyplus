# EnergyPlus weather data

## instantaneous/summed/meaned variables

Epw contains three types of variables. They are quite clearly defined in documentation.

*All variables definition containing "at the time indicated" (Auxiliary Programs 9.2, p63) are instantaneous.*

## right/left convention

**An epw has right convention**

Evidence:
 - for summed (example: dirnorrad, difhorrad...), it is clearly stated in documentation (and confirmed by interpolation algorithm - see below):
   - Auxiliary Programs 9.2, p63, §2.9.1.4 Field hour: "This is the hour of the data. (1 - 24). Hour 1 is 00:01 to 01:00.".
 - for instantaneous values:
   - it is not very clear in documentation weather hour 1 is 00:00 or 01:00. 
   The field minute is defined: Auxiliary Programs 9.2, p63, §2.9.1.5 Field minute: "This is the minute field. (1..60)" ; 
   but example weather files all have minute 0.
   - the analysis of the interpolation algorithm proves that it is at 01:00 (see below)
   - this conclusion is coherent with classical weather data for which 01:00 timestamped data corresponds to 01:00 instant for instantaneous data, and ]00:00;01:00] for summed

=> An epw day goes from hour 1 to hour 24.

=> Not sure about the meaning of minute because in weather example files (for example 9.2 Weather Data, San
    Fransisco, minutes are always 0 although they should be 60). Not important for us because we only manage
    hourly inputs: minutes are not taken into account.

=> summed or average data covers ]00:00,01:00], instantaneous data is at 01:00
 
## e+ interpolation algorithm

*see github EnergyPlus repo, tag v9.2.0, file src/EnergyPlus/WeatherManager.cc*

This algorithm is explained for an hourly epw, with a sub-hourly e+ timestep (we use 10 minutes for following explanation)

1: new epw row is retrieved InterpretWeatherDataLine (:3760), stored in tomorrow variables (for example TomorrowOutDewpointTemp) (:3452) at timestep 0.

*TomorrowOutDewpointTemp is an array of 24 columns (hourly), and 6 rows (timesteps.)*

2: interpolation of other timesteps is performed (:3596)
  - for instantaneous data, it is a linear interpolation with previous timestep. 
  *For first hour of first day, value at 00:00 is unknown, so value at 00:00 of next day (hour 24) is used (:3544).*
  - with the exception of LiquidPrecip, which is declared as instantaneous data, but in fact is sum, and is transformed to a summed data by diving by 6 after simple interpolation (complex solar interpolation - see below - is not used)
  - for summed data, a more complex algorithm is used, based on following explanation: 
  Engineering reference, p191, §5.1.6, "for interpolation of hourly weather data, the summed value is considered as the mean power at the midpoint of the hour. This point is then used for sub-hourly interpolation".
  WtNow is calculated (see :3591 and :9870) to apply the algorithm.
  *for this algorithm, to calculate last hour of day n, first hour of day n+1 is needed, although not available at current runtime. To manage this case, next hour of beam solar and dif solar is considered same as first hour of current day (which is ok since no sun at midnight...)*
 
 
## daylight savings
Epw weather series are in tzt (time zone time, without daylight savings). 
Daylight savings will be taken into account in simulation if epw or idf parameter is filled (schedules are converted to dst and outputs remain tzt).
 
 
## useful info
* dirnorrad (direct normal radiation) is called BeamSolarRad in e+ source code (github EnergyPlus repo, tag v9.2.0, file src/EnergyPlus/WeatherManager.cc, :4208)
