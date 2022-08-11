import platform
import threading
import time

import fluidsynth


class MusicView:
    """
    Wrapper for fluidsynth and its sequencer, so that music can be "viewed" i.e. listen to.
    """

    def __init__(self, model, ctrl):
        self.model = model
        self.ctrl = ctrl
        self.synth = fluidsynth.Synth()
        self.sequencer = fluidsynth.Sequencer(time_scale=1000)
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

    def stop(self):
        pass
        # print("stopped playing at {} with {} notes in queue".format(self.sequencer.get_tick(), self.model.notes.qsize()))

    def consume(self):
        """
        Threaded.
        Consume notes generated by music_model and feed them to the sequencer at regular interval.
        """
        while True:  # This thread never stops.
            self.ctrl.playingEvent.wait()  # Wait for the playing event
            self.ctrl.pausedEvent.wait()  # Wait for the playing event
            self.ctrl.fullSemaphore.acquire() #Wait for the queue to have at least 1 note
            self.ctrl.queueSemaphore.acquire() #Check if the queue is unused
            try:
                note = self.model.notes.get_nowait()
                self.ctrl.queueSemaphore.release() #Release queue
                self.ctrl.emptySemaphore.release() #Inform producer that there is room in the queue

                note_timing_abs = self.model.get_absolute_note_timing(note)  # tfactor to sec to ms
                current_time = self.sequencer.get_tick()
                # relative timing: how many ms a note has to wait before it can be played.
                #i.e. in how many ms should this note be played
                note_timing = int(note_timing_abs - (current_time - self.starting_time))
                while (note_timing > self.model.timeSettings.timeBuffer): #Check if the note should be played soon
                    time.sleep(self.model.timeSettings.timeBuffer / 2000)  # if not, wait half the buffer time
                    self.ctrl.pausedEvent.wait() #If paused was pressed during this waiting time, wait for PLAY event
                    current_time = self.sequencer.get_tick()
                    note_timing = int(note_timing_abs - (current_time - self.starting_time))  # update timing
                if (self.ctrl.playing):
                    print( "{}-{} new note with idx {} scheduled in {}ms (abs: {}ms-{}ms={}ms): {}. {} notes remaining in queue".format(
                            current_time, self.starting_time,
                            note.id,
                            note_timing,
                            note_timing_abs, self.sequencer.get_tick() + note_timing,
                                             self.sequencer.get_tick() + note_timing - note_timing_abs,
                            note,
                            self.model.notes.qsize()))
                    self.sequencer.note(absolute=False, time=int(note_timing), channel=note.channel, key=note.value,
                                        duration=note.duration, velocity=note.velocity, dest=self.registeredSynth)

            except IndexError:
                print("Empty notes queue")
                self.ctrl.queueSemaphore.release() #Release semaphores
                self.ctrl.emptySemaphore.release()

