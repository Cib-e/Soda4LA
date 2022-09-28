from Ctrls.parameter_encoding_controller import ParameterEncodingCtrl
from Models.data_model import Data
from Models.note_model import note_to_int
from Utils.constants import ENCODING_OPTIONS
from Utils.filter_module import FilterModule


class ParameterEncoding:
    """
    Model class for parameters encoding. It enables raw data to be processed into notes. Each track has its own parameter
    encoding objects.
    This can be viewed via a track config view and its subsequent views presented by its buttons.
    """

    def __init__(self, encoded_var: str, default_col=""):
        # Data
        self.encoded_var = encoded_var  # a variable of a note, value duration or velocity
        if self.encoded_var not in ENCODING_OPTIONS:
            raise NotImplementedError("{} not in encoding options".format(self.encoded_var))
        self.filter = FilterModule()  # Filter module applied to mainVar
        self.handpicked = True  # if true, uses handpickedEncoding to compute a parameter for a note, if not it uses functionEncoding
        self.handpickEncoding = {}  # Dictionary containing information to transform a row into a parameter for a note
        self.functionEncoding = {"min": 0,
                                 "max": 12 if self.encoded_var == "value" else 127}
        # Dictionary containing information to transform a row into a parameter for a note
        self.defaultValue = 80
        if self.encoded_var == "duration":
            self.defaultValue= 300
        elif self.encoded_var == "velocity":
            self.defaultValue = 127
        self.octave = "4" if self.encoded_var == "value" else "0"
        self.initialized = False

        # Others Models
        self.data = Data.getInstance()
        self.filter.column = self.data.get_variables()[0] if default_col == "" else default_col

        # Ctrl
        self.ctrl = ParameterEncodingCtrl(self)

        # Views
        self.peView = None

    def __getstate__(self):
        state = self.__dict__.copy()
        del state["ctrl"]
        del state["peView"]
        del state["data"]
        return state

    def __setstate__(self, state):
        self.__dict__.update(state)
        self.ctrl = ParameterEncodingCtrl(self)
        self.peView = None
        self.data = Data.getInstance()

    def get_parameter(self, row):
        """
        Compute and return a value for the parameter selected for this model, based on the filter selected by the user
        and the encoding.
        :param row: Pandas Dataframe,
            a row containing data to transform into a parameter
        :return: int,
            a value between 0 and 128 used as a parameter for a note
        """

        try:
            if (row[self.filter.column] == None):
                return self.defaultValue
            if self.handpicked:
                if (row[self.filter.column] not in self.handpickEncoding):
                    return self.defaultValue
                return int(self.handpickEncoding[row[self.filter.column]])
            else:
                return int(self.evaluate_with_fonction(row[self.filter.column]))
        except KeyError:
            print("Error while getting a value with {}".format(self.encoded_var))
            return self.defaultValue

    def evaluate_with_fonction(self, value):
        return_value = self.defaultValue
        if (self.functionEncoding["function"] == "linear"):
            ratio = float((self.data.get_min(self.filter.column)) / self.data.get_max(self.filter.column))
            return_value = int(float(value) * ratio)
        else:
            raise NotImplementedError()
        return return_value if self.encoded_var != "value" else return_value + 12 * int(self.octave)

    def assign_function_encoding(self, function: str, min_val: int, max_val: int):
        """
        Assign a function with parameter as encoding, according to user preference
        :param function: type of encoding to use, such as linear or log
        :param min_val: lower bound of selected function
        :param max_val: upper bound of selected function
        """
        self.functionEncoding["function"] = function
        self.functionEncoding["min"] = min_val
        self.functionEncoding["max"] = max_val

    def assign_handpicked_encoding(self, variables: [], values: [], octave="4"):
        """
        Assign values to variable, accordingly to user preference.
        :param variables: list,
            a list of all possible instances of a variable
        :param values: list,
            a list linked to the variable, used to compute a notes parameter
        """
        if (len(variables) != len(values)):
            raise ValueError()
        for var, val in zip(variables, values):
            # self.handpickEncoding[var] = []
            self.handpickEncoding[var] = note_to_int(val, int(octave)) if self.encoded_var == "value" else val
        self.defaultValue = note_to_int(values[0], int(octave)) if self.encoded_var == "value" else values[0]
        self.octave = octave

    def get_variables_instances(self):
        varins = ["default"]
        varins.extend(self.data.get_variables_instances(self.filter.column))
        return varins
