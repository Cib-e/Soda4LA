from Utils.constants import SOUNDFONTS

from Views.track_config_view import TrackConfigView
from Views.track_midi_view import TrackMidiView


class TrackCtrl:
    """
    Controller for a track. each track have its own ctrl and its own views.
    """

    def __init__(self, model):
        # Model
        self.model = model  # Track Model

    def setup(self, config_view: TrackConfigView, midi_view: TrackMidiView):
        self.model.configView = config_view
        self.model.midiView = midi_view
        self.change_gain(100)

    def update_filter(self, filter: str):
        self.model.filter.assign(filter)

    def set_soundfont(self, soundfont: str):
        self.model.soundfont = SOUNDFONTS[soundfont]
        self.model.music.ctrl.load_soundfonts()

    def set_main_var(self, column: str):
        self.model.set_main_var(column)

    def change_gain(self, gain: int):
        self.model.gain = int(gain)
        self.model.music.ctrl.change_gain(self.model.id, self.model.gain)
        if (self.model.midiView.local_gain_slider.get() != gain):
            self.model.midiView.local_gain_slider.set(gain)
        if (self.model.configView.local_gain_slider.get() != gain):
            self.model.configView.local_gain_slider.set(gain)

    def mute_track(self):
        self.model.muted = not self.model.muted
        self.model.music.ctrl.change_gain(self.model.id, 0) if self.model.muted \
            else self.model.music.ctrl.change_gain(self.model.id, self.model.gain)

    def remove(self):
        for pencoding_model in self.model.pencodings.values():
            pencoding_model.ctrl.destroy()
        self.model.remove()

    def open_encoding(self, encoded_var: str):
        self.model.pencodings[encoded_var].ctrl.show_window()
