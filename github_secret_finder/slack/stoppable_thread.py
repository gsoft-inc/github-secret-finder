import threading


class StoppableThread(threading.Thread):

    def __init__(self, action, sleep):
        super(StoppableThread, self).__init__()
        self._action = action
        self._sleep = sleep
        self._stop = threading.Event()

    def run(self):
        while not self.stopped():
            self._stop.wait(self._sleep)
            self._action()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()
