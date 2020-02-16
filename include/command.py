from datetime import datetime, timedelta
import logging


class Command:
    def __init__(self, message, max_retry_attempts, wait_time_seconds, logger=None):
        self.message = message
        self.max_retry_attempts = max_retry_attempts
        self.wait_time_seconds = wait_time_seconds
        self.send_attempts = 0
        self.first_sent_datetime = None
        self.last_sent_datetime = None
        self.completed_datetime = None
        self.success = None
        self.logger = logger

    def log(self, msg, level=logging.INFO):
        if self.logger:
            self.logger.log(level, msg)

    def invalid_message(self, message):
        """ Check if the incoming serial message is 'INVALID' """
        if message == 'INVALID':
            self.success = False
            self.log('[COMMAND]Invalid command. Dropping command...')
            return True
        return False

    def success_message(self, message):
        """ Check if the incoming serial message is the same as the command message """
        if message == self.message:
            self.success = True
            self.completed_datetime = datetime.now()
            self.log('[COMMAND]Command completed. {} attempt(s) with total time {} seconds to complete'
                     .format(self.send_attempts, (self.completed_datetime - self.first_sent_datetime).total_seconds()))
            return True
        return False

    def attempts_maxed(self):
        """ Check if the maximum attempts has been reached """
        maxed = self.max_retry_attempts <= self.send_attempts
        if maxed:
            self.log('[COMMAND]Command attempts have been maxed. Dropping command...')
            return True
        return False

    def ready_to_send(self):
        """ Check if the timeout period has been reached and the command is ready to resent """
        if not self.last_sent_datetime:
            return True

        if self.last_sent_datetime + timedelta(seconds=self.wait_time_seconds) < datetime.now():
            return True
        return False

    def send_message(self):
        """ Return the message string to be sent and update the command details """
        now = datetime.now()
        if not self.first_sent_datetime:
            self.first_sent_datetime = now
        self.send_attempts += 1
        self.last_sent_datetime = now
        self.log('[COMMAND]Sending command. Attempt {}/{}'.format(self.send_attempts, self.max_retry_attempts))
        return self.message
