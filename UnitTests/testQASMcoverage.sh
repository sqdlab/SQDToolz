coverage erase
coverage run --branch --include="*/sqdtoolz/Utilities/OpenQASM/ParserOpenQASM.py" -m unittest UnitTests.testQASM
coverage report -m
coverage html
