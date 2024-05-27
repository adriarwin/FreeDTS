import argparse
import os
import numpy as np
import frame
import matplotlib.pyplot as plt
import time
import re

"""Things to be done:
1. Create file indicating shape of each array!
2. Create file indicating properties of the analysis?"""

class Universe:
    def __init__(self, input_arguments):

        #predefined variables
        self.name_TrjTSI_folder='TrjTSI'
        self.area_filename='area'
        self.projected_area_filename='projected_area'
        self.membrane_thickness_filename='thickness'
        self.fluctuation_spectrum_filename='fluctuation_spectrum'
        self.energy_filename='energy'
        self.energy_steps_filename='energy_MCsteps'
        self.inclusion_average_neighbours_filename='inclusion_average_neighbours'
        self.inclusion_cluster_filename='inclusion_cluster_statistics'
        self.qvec_filename='q2vec'
        self.frame_steps_filename='frame_steps'
        self.original_energy_filename='output-en.xvg'
        self.output_analysis_filename='analysis_output.txt'

        #input file variables
        self.directory_path = None
        self.name_output_files = ''
        self.name_output_folder = None
        self.path_output_folder = None
        self.initial_step = None
        self.final_step = None
        self.area_calculation = None
        self.inclusion_average_neighbours_calculation = None
        self.inclusion_cluster_statistics_calculation = None
        self.fluctuation_spectrum_planar_calculation = None
        self.bx=None
        self.by=None
        self.membrane_thickness_calculation = None
        self.energy_calculation = None
        self.path_input_dts=None
        self.fluctuation_spectrum_no_inclusions = "off"
        self.kappa=None
        self.kappag=None
        self.inclusion_kappa=None
        self.inclusion_Co=None
        self.inclusion_kappag=None
        self.inclusion_density=None
        self.parallel_tempering=None
        self.stupid_counter=0
        
        
        self.output_folder_path=None

        #assigning
        self.parse_input_file(input_arguments.input_file)

        for attr, value in vars(input_arguments).items():
            if value is not None:
                setattr(self, attr, value)
        
        


        self.frame_path_list=np.array([],dtype=str)

        #Checking existance of frames 
        for i in range(self.initial_step,self.final_step+1):
            
            #Checking existence of frame i
            file_path_existence,file_path=self.check_frame_existence(i)

            if file_path_existence:
                # Check if the file is empty
                if os.path.getsize(file_path) == 0:
                    print(f"File {file_path} exists but is empty.")
                else:
                    self.frame_path_list = np.append(self.frame_path_list, file_path)
                
        #Terminating program if there are no frames

        if self.frame_path_list.size==0:
            raise ValueError("There are no tsi files in the indicated path and tsi files range")   
        
        else:
            self.nframes=self.frame_path_list.size
            self.frame_num_list=range(0,self.nframes)
        
        self.frame_num_list=np.array(self.frame_num_list,dtype=int)
        #initializing important parameters from .tsi files and input.dts file


        frame_object=frame.frame(self.frame_path_list[0])
        
        self.path_input_dts=os.path.join(self.directory_path,"input.dts")
        print(self.path_input_dts)

        self.extract_parameters_dts()



        #making sure that no inclusion functions are turned off in absence of inclusions

        self.ninclusion=frame_object.ninclusion
        if self.ninclusion==0:
            self.inclusion_average_neighbours_calculation = None
            self.inclusion_cluster_statistics_calculation = None

            if self.fluctuation_spectrum_planar_calculation=="on":
                self.fluctuation_spectrum_no_inclusions="on"
        
        del frame_object
            

        #Creation of folder where I will keep my data:

        if self.name_output_folder:
            # Create the full path for the output folder
            self.output_folder_path = os.path.join(self.directory_path, self.name_output_folder)
            # Create the folder if it doesn't exist
            if not os.path.exists(self.output_folder_path):
                os.makedirs(self.output_folder_path)

        else:
            self.name_output_folder='analysis_output'
            self.output_folder_path = os.path.join(self.directory_path, self.name_output_folder)
            # Create the folder if it doesn't exist
            if not os.path.exists(self.output_folder_path):
                os.makedirs(self.output_folder_path)

        #Save stuff...
            

    

        #initialization of different variables based on input
        self.area_array= None
        self.projected_area_array= None
        self.inclusion_average_neighbours_array = None
        self.inclusion_cluster_statistics_array = None
        self.fluctuation_spectrum_planar_array = None
        self.membrane_thickness_array=None
        self.energy_array=None
        self.energy_MCsteps_array=None
        

        self.array_initialization()

        if self.energy_calculation=="on":
            path=os.path.join(self.directory_path,self.original_energy_filename)
            self.obtain_energy(path)
            pass

        self.iteration()
        
        self.save_data()


    def extract_parameters_dts(self):
    
        print('here')
        inclusion_parameters = []
        density = None

        with open(self.path_input_dts, 'r') as file:
            for line in file:
                line = line.strip()

                # Extract kappa
                if line.startswith("Kappa"):
                    variable, value = line.split('=')
                    floats = [float(x) for x in value.split()]
                    print(floats)
                    self.kappa = floats[0]
                    self.kappag =floats[1]

                # Extract inclusion parameters
                if line.startswith("1"):
                    params = line.split()
                    if len(params) >= 7:
                        third_number = float(params[2])
                        forth_number = float(params[3])
                        seventh_number = float(params[6])
                        inclusion_parameters.append([third_number, forth_number, seventh_number])

                # Extract density
                if line.startswith("Density"):
                    density_match = re.match(r'Density\s+(\S+)', line)
                    if density_match:
                        self.inclusion_density = float(density_match.group(1))

        self.inclusion_kappa=inclusion_parameters[0][0]-self.kappa
        self.inclusion_kappag=inclusion_parameters[0][1]-self.kappag
        self.inclusion_Co=inclusion_parameters[0][2]

    
    def write_output_file(self,output_path):
        content = f"Initial step={self.initial_step}\n" \
              f"Final step={self.final_step}\n" \
              f"kappa={self.kappa}\n" \
              f"kappa_g={self.kappag}\n" \
              f"inclusion_kappa={self.inclusion_kappa}\n" \
              f"inclusion_kappa_g={self.inclusion_kappag}\n" \
              f"inclusion_Co={self.inclusion_Co}\n" \
              f"inclusion_density={self.inclusion_density}\n"

        # Write the content to the file
        with open(output_path, 'w') as file:
            file.write(content)


    def obtain_energy(self, path):
        print('obtaining energy')
        try:
            with open(path, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print("File not found:", path)
            return

        # Initialize lists to store data
        mcstep = []
        energy = []

        # Parse each line and extract data
        for line in lines:
            # Skip lines starting with '#' or empty lines
            if line.startswith('#') or not line.strip():
                continue
            # Split line by whitespace and extract the first two columns
            columns = line.split()
            if len(columns) < 2:
                print("Skipping line with unexpected format:", line.strip())
                continue
            try:
                mcstep.append(int(columns[0]))
                energy.append(float(columns[1]))
            except (IndexError, ValueError):
                print("Skipping line with unexpected format:", line.strip())

        # Convert lists to numpy arrays
        self.energy_MCsteps_array = np.array(mcstep)
        self.energy_array = np.array(energy)
        print('energy correct')



    def parse_input_file(self, input_file):
        with open(input_file, 'r') as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                variable, value = line.split('=')
                variable = variable.strip()
                value = value.strip()

                if variable == 'fluctuation_spectrum_planar_calculation':
                    auxiliar=value.split()
                    value=auxiliar[0]
                    self.bx=int(auxiliar[1])
                    self.by=int(auxiliar[2])
                    
                
                if variable == 'initial_step':
                    value=int(value)

                if variable == 'final_step':
                    value=int(value)
                

                setattr(self, variable, value)

    def save_data(self):

        #Save data
        file_path=os.path.join(self.output_folder_path,self.output_analysis_filename) + self.name_output_files

        self.write_output_file(file_path)
        
        file_path=os.path.join(self.output_folder_path,self.frame_steps_filename)+self.name_output_files
        np.save(file_path,self.frame_num_list)
        


        if self.area_calculation=="on":
            file_path_area=os.path.join(self.output_folder_path,self.area_filename)+self.name_output_files
            file_path_projected_area=os.path.join(self.output_folder_path,self.projected_area_filename)+self.name_output_files
            np.save(file_path_area,self.area_array)
            np.save(file_path_projected_area,self.projected_area_array)

        
        if self.inclusion_average_neighbours_calculation=="on":
            file_path=os.path.join(self.output_folder_path,self.inclusion_average_neighbours_filename)+self.name_output_files
            np.save(file_path,self.inclusion_average_neighbours_array)
        
        if self.inclusion_cluster_statistics_calculation=="on":
            #Since maximum cluster size is the number of inclusions:
            file_path=os.path.join(self.output_folder_path,self.inclusion_cluster_filename)+self.name_output_files
            np.save(file_path,self.inclusion_cluster_statistics_array)

        if self.fluctuation_spectrum_planar_calculation=="on":
            file_path_fs=os.path.join(self.output_folder_path,self.fluctuation_spectrum_filename)+self.name_output_files
            file_path_qvec=os.path.join(self.output_folder_path,self.qvec_filename)+self.name_output_files
            np.save(file_path_fs,self.fluctuation_spectrum_planar_array)
            np.save(file_path_qvec,self.q2vec_array)

        if self.membrane_thickness_calculation=="on":
            file_path=os.path.join(self.output_folder_path,self.membrane_thickness_filename)+self.name_output_files
            np.save(file_path,self.membrane_thickness_array)

        if self.energy_calculation=="on":
            file_path_energy=os.path.join(self.output_folder_path,self.energy_filename)+self.name_output_files
            file_path_energy_steps=os.path.join(self.output_folder_path,self.energy_steps_filename)+self.name_output_files
            np.save(file_path_energy,self.energy_array)
            np.save(file_path_energy_steps,self.energy_MCsteps_array)
            



    def array_initialization(self):

        if self.area_calculation=="on":
            
            self.area_array=np.zeros((self.nframes),float)
            self.projected_area_array=np.zeros((self.nframes),float)

        if self.inclusion_average_neighbours_calculation=="on":
            self.inclusion_average_neighbours_array=np.zeros((self.nframes),float)

        if self.inclusion_cluster_statistics_calculation=="on":
            #Since maximum cluster size is the number of inclusions:
            self.inclusion_cluster_statistics_array=np.zeros((self.nframes,self.ninclusion),float)

        if self.fluctuation_spectrum_planar_calculation=="on":
            self.q2vec_array=np.zeros((self.nframes,self.by+1,2*self.bx+1),dtype=float)
            if self.fluctuation_spectrum_no_inclusions=="off":
                self.fluctuation_spectrum_planar_array=np.zeros((self.nframes,self.by+1,2*self.bx+1,2,2),dtype=complex)
            else:
                self.fluctuation_spectrum_planar_array=np.zeros((self.nframes,self.by+1,2*self.bx+1),dtype=complex)

        if self.membrane_thickness_calculation=="on":
            self.membrane_thickness_array=np.zeros((self.nframes),float)
    

    def check_frame_existence(self,index):
        """Checks the existance of frame with a given index, and gives the path to the frame with index
        index."""

        # Construct the filename based on the index
        filename = f"output{index}.tsi"
        file_path = os.path.join(self.directory_path,self.name_TrjTSI_folder,filename)

        return os.path.exists(file_path),file_path

    


    def perform_calculation(self,file_path,i):
        
        frame_object=frame.frame(file_path)
        i=i+self.stupid_counter
        """
        self.inclusion_average_neighbours_calculation = None
        self.inclusion_cluster_statistics_calculation = None
        self.fluctuation_spectrum_planar_calculation = None
        self.bx=None
        self.by=None
        self.membrane_thickness_calculation = None"""

        try:
            if self.area_calculation=="on":
                frame_object.area_calculation()
                self.area_array[i]=frame_object.area
                self.projected_area_array[i]=frame_object.projected_area

                pass

            if self.inclusion_average_neighbours_calculation=="on":
                frame_object.inclusion_connectivity()
                self.inclusion_average_neighbours_array[i]=frame_object.inclusion_average_neighbours
                pass

            if self.inclusion_average_neighbours_calculation=="on" and self.inclusion_cluster_statistics_calculation=="on":
                frame_object.inclusion_cluster()
                self.inclusion_cluster_statistics_array[i,frame_object.inclusion_cluster_sizes]=frame_object.inclusion_cluster_frequency

            if self.inclusion_average_neighbours_calculation=="off" and self.inclusion_cluster_statistics_calculation=="on":
                frame_object.inclusion_connectivity()
                frame_object.inclusion_cluster()
                self.inclusion_cluster_statistics_array[i,frame_object.inclusion_cluster_sizes]=frame_object.inclusion_cluster_frequency

            if self.fluctuation_spectrum_planar_calculation=="on":
                if self.fluctuation_spectrum_no_inclusions=="off":
                    self.fluctuation_spectrum_planar_array[i,:,:,:,:],self.q2vec_array[i,:,:]=frame_object.ft_matrix(self.bx,self.by)
                else:
                    self.fluctuation_spectrum_planar_array[i,:,:],self.q2vec_array[i,:,:]=frame_object.ft_matrix_no_inc(self.bx,self.by)

            if self.membrane_thickness_calculation=="on":
                self.membrane_thickness_array[i]=frame_object.thickness

        except Exception as e:
            print("An error occurred while performing calculation for frame {}: {}".format(i, e))
            """Now I want this code to be modified. I would like to eliminate to pop the elemnt i from each
            of the lists after the conditionals. Also, I would like to modify the self.frame_num_list and 
            also eliminate its element i. """

            if self.area_calculation == "on":
                self.area_array = np.delete(self.area_array, i, axis=0)
                self.projected_area_array = np.delete(self.projected_area_array, i, axis=0)

            if self.inclusion_average_neighbours_calculation == "on":
                self.inclusion_average_neighbours_array = np.delete(self.inclusion_average_neighbours_array, i, axis=0)

            if self.inclusion_average_neighbours_calculation == "on" and self.inclusion_cluster_statistics_calculation == "on":
                self.inclusion_cluster_statistics_array = np.delete(self.inclusion_cluster_statistics_array, i, axis=0)

            if self.inclusion_average_neighbours_calculation == "off" and self.inclusion_cluster_statistics_calculation == "on":
                self.inclusion_cluster_statistics_array = np.delete(self.inclusion_cluster_statistics_array, i, axis=0)

            if self.fluctuation_spectrum_planar_calculation == "on":
                self.fluctuation_spectrum_planar_array = np.delete(self.fluctuation_spectrum_planar_array, i, axis=0)
                self.q2vec_array = np.delete(self.q2vec_array, i, axis=0)

            if self.membrane_thickness_calculation == "on":
                self.membrane_thickness_array = np.delete(self.membrane_thickness_array, i, axis=0)

            self.frame_num_list=np.delete(self.frame_num_list,i)

            self.stupid_counter-=1
        
            



        #perform calculations
    
    def iteration(self):

        """Iterates over the desired frames and obtains quantities specified
        in the input file."""

        for i in range(0,len(self.frame_path_list)):

            #start_time = time.time()

            self.perform_calculation(self.frame_path_list[i],i)


            #end_time = time.time()

            #elapsed_time = end_time - start_time
            #print("Percentatge",i/(self.frame_num_list[-1]),"Elapsed time:", elapsed_time, "seconds")

        
        
        

def main():
    parser = argparse.ArgumentParser(description="Process input parameters")
    parser.add_argument("-i", "--input_file", help="Path to input file", required=True)
    parser.add_argument("-d", "--directory_path", help="Path to data directory")
    parser.add_argument("-o", "--name_output_files", help="Name for output files")
    parser.add_argument("-f", "--name_output_folder", help="Name for output folder")
    parser.add_argument("-p", "--path_output_folder", help="Path to output folder")
    parser.add_argument("-e", "--initial_steps", help="Equilibration steps")
    parser.add_argument("-s", "--final_steps", help="Number of final steps")
    """
    parser.add_argument("-a", "--area", help="Area calculation", choices=["on", "off"])
    parser.add_argument("-n", "--inclusion_average_neighbours", help="Inclusion average neighbours calculation", choices=["on", "off"])
    parser.add_argument("-c", "--inclusion_cluster_statistics", help="Inclusion cluster statistics calculation", choices=["on", "off"])
    parser.add_argument("-m", "--membrane_thickness", help="Membrane thickness calculation", choices=["on", "off"])
    parser.add_argument("-g", "--energy", help="Energy calculation", choices=["on", "off"])"""
    
    import time

    start_time = time.time()
    # Your code or task here
    

    args = parser.parse_args()

    calculation = Universe(args)


    end_time = time.time()

    elapsed_time = end_time - start_time
    print("Elapsed time:", elapsed_time, "seconds")



if __name__ == "__main__":
    main()
