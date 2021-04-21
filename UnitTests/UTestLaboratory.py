from sqdtoolz.ExperimentConfiguration import*
from sqdtoolz.Laboratory import*

#Test cold-reload
new_lab = Laboratory('UnitTests\\UTestExperimentConfiguration.yaml', 'test_save_dir')

with open("UnitTests/laboratory_configuration.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_instruments(data)
with open("UnitTests/next_test.txt") as json_file:
    data = json.load(json_file)
    new_lab.cold_reload_configuration(data)

print("Laboratory Unit Tests completed successfully.")
