from random import uniform

class WeatherGenerator:
   
    def __init__(self):
        ''' Class constructor. 
        '''
        pass

    def measure_wind(self, interval):
        ''' Simulate a wind measurement (km/h). 

            Paramenters:
                interval ([float, float]) :  Sample a value in this interval   
        ''' 
        return uniform(interval[0], interval[1])
    
    def measure_temperature (self, interval):
        ''' Simulate a temperature measurement (Celsius). 

            Paramenters:
                interval ([float, float]) :  Sample a value in this interval   
        '''
        return uniform(interval[0], interval[1])