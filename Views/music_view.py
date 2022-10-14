import platform
import threading
import time
from queue import Empty

import numpy as np

# import fluidsynth as m_fluidsynth
from Models.note_model import int_to_note
from Utils import m_fluidsynth


class MusicView:
    """
    Wrapper for fluidsynth and its sequencer, so that music can be "viewed" i.e. listen to.
    """

    def __init__(self, model, ctrl):
        self.model = model
        self.ctrl = ctrl
        self.synth = m_fluidsynth.Synth()
        self.sequencer = m_fluidsynth.Sequencer(time_scale=self.model.timescale)
        self.registeredSynth = self.sequencer.register_fluidsynth(self.synth)
        # self.seqIds = self.sequencer.register_client("callback", self.wrap_consume)
        self.now = None
        self.starting_time = None
        self.pause_start_time = None
        self.consumer_thread = threading.Thread(target=self.consume, daemon=True)
        self.consumer_thread.start()

        print("platform {} detected ".format(platform.system()))

        # Start the synth so its ready to play notes
        if platform.system() == "Windows":
            # Use the line below if for MS Windows driver
            self.synth.start()
        else:
            self.synth.start(driver="alsa")
            # you might have to use other drivers:
            # fs.start(driver="alsa", midi_driver="alsa_seq")

    def save_play_time(self):
        if (not self.ctrl.playing):  # If we are starting a new music, register the starting time
            self.starting_time = self.sequencer.get_tick()
            print("started playing from origin: {}".format(self.starting_time))
        elif (self.ctrl.paused):  # If the model was paused, increment starting time by pause time
            paused_time = self.sequencer.get_tick() - self.pause_start_time
            self.starting_time += paused_time
            print("started playing from unpaused: {}".format(self.starting_time))
        else:
            raise RuntimeError("Issue with play/pause/stop logic.")

    def save_pause_time(self):
        self.pause_start_time = self.sequencer.get_tick()  # Register when the pause button was pressed
        print("pausing at : {}".format(self.pause_start_time))

    def consume(self):
        """
        Threaded.
        Consume notes generated by music_model and feed them to the sequencer at regular interval.
        """
        prev_note_idx = 0
        while True:  # This thread never stops.
            self.ctrl.playingEvent.wait()  # Wait for the playing event
            self.ctrl.pausedEvent.wait()  # Wait for the playing event
            self.ctrl.fullSemaphore.acquire()  # Wait for the queue to have at least 1 note
            self.ctrl.queueSemaphore.acquire()  # Check if the queue is free
            try:
                note = self.model.notes.get_nowait()
                self.ctrl.queueSemaphore.release()  # Release queue
                self.ctrl.emptySemaphore.release()  # Inform producer that there is room in the queue
                # relative timing: how many ms a note has to wait before it can be played.
                # i.e. in how many ms should this note be played
                note_timing_abs = self.model.get_absolute_note_timing(note.tfactor)
                note_timing = self.get_relative_note_timing(note_timing_abs)  # update timing
                while (note_timing > self.model.timeSettings.timeBuffer and  # check if next note is ripe
                       not self.ctrl.skipNextNote and  # check if next note should be skipped
                       note_timing > -100 and self.ctrl.playing):  # Check if the note is not stale
                    time.sleep(self.model.timeSettings.timeBuffer / 2000)  # wait half the buffer time
                    self.ctrl.pausedEvent.wait()  # If paused was pressed during this waiting time, wait for PLAY event
                    note_timing = self.get_relative_note_timing(note_timing_abs)  # update timing

                if (self.ctrl.playing and note_timing > -100 and not self.ctrl.skipNextNote):
                    #log_line = self.write_log_line(note, track_log_str, note_timing, note_timing_abs, prev_note_idx)
                    self.sequencer.note(absolute=False, time=int(note_timing), channel=note.channel, key=note.value,
                                        duration=note.duration, velocity=note.velocity, dest=self.registeredSynth)
                else:
                    self.ctrl.skipNextNote = False  # Once the note is skipped, don't skip the next ones
                    log_line = "SKIPPED Note [track={}, value={}, vel={}, dur={}, timing abs={}] at t={}, data row #{} planned scheduled in {}ms. {} notes remaining".format(
                        note.channel, int_to_note(note.value), note.velocity, note.duration, note_timing_abs,
                        self.sequencer.get_tick(), note.id, note_timing, self.model.notes.qsize())
                    print(log_line)
                if(prev_note_idx != note.id):
                    threading.Thread(target=self.model.sonification_view.tableView.model.pushRowToDataFrame(note_timing), daemon=True).start()
                prev_note_idx = note.id

                #self.model.sonification_view.add_log_line(log_line)
            except Empty:
                print("Empty notes queue")
                self.ctrl.queueSemaphore.release()  # Release semaphores
                self.ctrl.emptySemaphore.release()

    def write_log_line(self, note, track_log_str, note_timing, note_timing_abs, prev_note_idx):
        if (prev_note_idx != note.id):
            self.model.sonification_view.add_log_line("--------------------")
        print("Note #{} with tfactor {} and absolute position to {}. absolute distance with tick is {} and relative distance is {} or {}".format(note.id, note.tfactor,
                                                                       self.convert(note.tfactor, to_absolute=False),
                                                                       self.get_temporal_distance(note.tfactor,
                                                                                                  absolute=True),
                                                                       self.get_relative_note_timing(note_timing_abs),
                                                                       self.get_temporal_distance(self.convert(note.tfactor, False), False)))
        return "Note [track={}, value={}, vel={}, dur={}, timing abs={}] at t={}, data row #{} scheduled in {}ms. {} notes remaining".format(
            track_log_str, int_to_note(note.value), note.velocity, note.duration, note_timing_abs,
            self.sequencer.get_tick(), note.id, note_timing, self.model.notes.qsize())

    def get_relative_note_timing(self, note_timing_absolute):
        """
        :param note_timing_absolute: int:
            a value between 0 and model.musicDuration
        :return:
            the temporal distance (ms) between get_tick() and the input
        """
        return int(note_timing_absolute - (self.sequencer.get_tick() - self.starting_time))



    def convert(self, temporal_pos, to_absolute=True):
        if to_absolute:
            return float(temporal_pos - self.starting_time) / (self.model.timeSettings.get_music_duration() * 1000)
        else:
            return (temporal_pos) * self.model.timeSettings.get_music_duration() * 1000 + self.starting_time

    def get_absolute_tick(self):
        return self.convert(self.sequencer.get_tick(), to_absolute=True)

    def set_relative_tick(self, absolute_tick):
        self.starting_time = self.sequencer.get_tick() - absolute_tick * self.model.timeSettings.get_music_duration() * 1000

    def get_temporal_distance(self, temporal_pos, absolute=True):
        if absolute:
            return temporal_pos - self.get_absolute_tick()
        else:
            return temporal_pos - self.sequencer.get_tick()

    """
    Absolute: between 0 and 1
    Relative: between N and music.duration + N
    Distance: between -music.duration and music.duration, temporal distance with ctp
    Current temporal position! Can be moved, stopped, etc. in absolute space but is the slow and steady arrow of time
    in relative, get by .get_tick()
    -> Need conversion tools between absolute and relative temporal position
    Modify relative bounds to change behavior
    pause simply pauses ctp in absolute, but in relative it prevents production and consumtion of notes, and then increments N by pause_time at the end of pause.
    stop simply pauses and set ctp to 0 in absolute, but in relative it pauses, reset data idx to 0, empty queue and then unpause at the start of new music/
    fbw simply moves ctp by -10 in absolute, but in relative it pauses, moves idx by -10, empty queue, and then unpause
    """
