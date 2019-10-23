import threading


class StoppableThread(threading.Thread):

    def __init__(self, action, stop_action, sleep):
        super(StoppableThread, self).__init__()
        self._action = action
        self._stop_action = stop_action
        self._sleep = sleep
        self._stop = threading.Event()

    def run(self):
        while not self.stopped():
            self._stop.wait(self._sleep)
            self._action()
        self._stop_action()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
