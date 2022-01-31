from sqdtoolz.Laboratory import Laboratory
from sqdtoolz.ExperimentSpecification import ExperimentSpecification

lab = Laboratory('', 'save_dir')

ExperimentSpecification('temp', lab)

ExperimentSpecification.list_SPEC_templates(True)

a=0