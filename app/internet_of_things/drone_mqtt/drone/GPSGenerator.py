from math import sqrt


def dist(pos1, pos2):
    return sqrt((pos2[0] - pos1[0])**2 + 
                (pos2[1] - pos1[1])**2) 


def norm(vec):
    norm = 0
    for v in vec:
        norm += v**2
    
    return sqrt(norm)


class GPSGenerator:
    def __init__(self, start_pos, target_pos, n_pos):
        ''' Class constructor. 

            Parameters:
                start_pos ([float,float])    : initial GPS coordinates [latitude, longitude]
                target_pos ([float,float])   : target GPS coordinates [latitude, longitude]
        '''
        self.start_pos = start_pos                                      # Starting GPS coordinates
        self.target_pos = target_pos                                    # Target GPS coordinates
        self.curr_pos = [0,0]                                           # Actual/current GPS coordinates

        # Compute distance between start and target positions
        self.start_target_dist = dist(self.target_pos, self.start_pos)

        # Compute increment between successive positions to have n_pos positions between start 
        # and target positions
        self.incr = self.start_target_dist / n_pos

        # Compute normalized direction vector between start and target positions
        direction_vec = [target_pos[0] - start_pos[0], target_pos[1] - start_pos[1]]
        self.direction_vec = [v/norm(direction_vec) for v in direction_vec] 

        # Set current position as the start position
        self.curr_pos = start_pos                                           

    def next_pos_on_line(self):
        ''' Return the next GPS measurement, and whether the target position has been reached.

            Return
                target_reached(boolean), GPS measurement ({})   
        '''
        self.curr_pos[0] += (self.direction_vec[0] * self.incr)
        self.curr_pos[1] += (self.direction_vec[1] * self.incr)

        return (dist(self.curr_pos, self.target_pos) < 0.001), {'type': 'Point', 'coordinates': self.curr_pos}