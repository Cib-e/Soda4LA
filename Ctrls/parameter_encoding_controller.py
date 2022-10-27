import logging

from Models.note_model import note_to_int, int_to_note


class ParameterEncodingCtrl:
    """
    Controller for the encoding view
    """

    def __init__(self, model):
        # Model
        self.model = model

    def assign_main_var(self, main_var):
        self.model.filter.assign_column(main_var)
        self.model.initialized = True

    def set_default_value(self, value):
        if value == "":
            return
        if self.model.encoded_var == "value":
            if value.isnumeric():
                try:
                    v = note_to_int(int_to_note(int(value)), int(self.model.octave))
                    self.model.defaultValue = v
                except ValueError:
                    logging.log(logging.ERROR,"Issue with value in setDefault-value {}".format(value))
            else:
                try:
                    v = note_to_int(str(value).upper(), int(self.model.octave))
                    self.model.defaultValue = v
                except ValueError:
                    logging.log(logging.ERROR,"Issue with value in setDefault-value-nonnum {}".format(value))
        elif value.isnumeric():
            self.model.defaultValue = int(value)

    def reset_value(self, variable):
        self.model.handpickEncoding.pop(variable, None)

    def set_value(self, value, variable):
        if value == "":
            return
        if self.model.encoded_var == "value":
            if value.isnumeric():
                try:
                    v = note_to_int(int_to_note(int(value)), int(self.model.octave))
                    self.model.handpickEncoding[variable] = v
                except ValueError:
                    return
            else:
                try:
                    v = note_to_int(str(value).upper(), int(self.model.octave))
                    self.model.handpickEncoding[variable] = v
                except ValueError:
                    return
        elif value.isnumeric():
            self.model.handpickEncoding[variable] = int(value)

    def change_octave(self, octave):
        #TODO Change octave location on view
        self.model.octave = octave
        for key in self.model.handpickEncoding:
            self.set_value(int_to_note(self.model.handpickEncoding[key]), key)
        self.set_default_value(int_to_note(int(self.model.defaultValue)))