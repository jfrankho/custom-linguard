from logging import warning, info
from threading import Thread, Event

import schedule


class CronManager:

    def __init__(self):
        self.started = False
        self.exit = Event()

    def start(self):
        if self.started:
            warning("Already started!")
            return
        info(f"Starting...")
        self.started = True
        self.exit.clear()
        Thread(target=self.__run_jobs__).start()
        info(f"Started.")

    def __run_jobs__(self):
        while not self.exit.is_set():
            n = schedule.idle_seconds()
            if n is None:
                self.exit.wait(30)
            elif n > 0:
                self.exit.wait(n)
            schedule.run_pending()

    def stop(self):
        if not self.started:
            warning("Not running!")
            return
        info(f"Stopping...")
        self.started = False
        self.exit.set()
        for job in schedule.jobs:
            schedule.cancel_job(job)
        info(f"Stopped.")


cron_manager = CronManager()
