import time
import src.utils.string_utils as string_utils
from statistics import mean


def get_time():
    return time.time()


class Timer:
    def __init__(self):
        self.start_time = None

    def start(self):
        start_time = time.time()
        self.start_time = start_time
        return "start time: " + time.strftime('%X %x', time.localtime(self.start_time))

    def stop(self):
        elapsed_time = time.time() - self.start_time
        return "elapsed_time: " + string_utils.stringify_time_delta(elapsed_time)


class StatusPrinter:
    def __init__(self, total_count, avoid_use_of_timer=True, start_print_interval=None, padding=''):
        self.avoid_use_of_timer = avoid_use_of_timer
        if not start_print_interval:
            start_print_interval = max(total_count / 10000, 1)

        self.total_count = total_count
        self.print_interval = start_print_interval  # auto updated to print every 30s
        self.current_count = 0
        self.last_current_count = 0
        self.last_print_time = get_time()
        self.padding = padding

        self.last_throughputs = []
        self.start_time = None

        self.last_operation_done_time = get_time() - 30

    def print_status(self):
        now = get_time()

        current_count = self.current_count
        elapsed_time = now - self.last_print_time

        throughput = (current_count - self.last_current_count) / elapsed_time
        percentage = round((current_count / self.total_count) * 100, 2)

        # compute throughput mean
        if len(self.last_throughputs) > 4:
            self.last_throughputs.pop(0)
        self.last_throughputs.append(throughput)
        throughput_mean = mean(self.last_throughputs)

        if throughput_mean > 0:
            eta = (self.total_count - current_count) / throughput_mean
        else:
            eta = -1
        eta_printable = string_utils.stringify_time_delta(eta)

        self.last_current_count = current_count
        self.last_print_time = now


        if throughput_mean > 1:
            throughput_printable = string_utils.stringify_int(throughput_mean) + ' element/s'
        else:
            throughput_printable = string_utils.stringify_int(throughput_mean * 60) + ' element/min'
        current_count_printable = string_utils.stringify_int(current_count)
        total_count_printable = string_utils.stringify_int(self.total_count)

        print(self.padding + 'loaded: {}% [eta: {}] [speed:{}] [processed: {}/{}]'.format(percentage, eta_printable, throughput_printable, current_count_printable, total_count_printable))
        return throughput

    def operation_done(self):
        if self.start_time is None:
            self.start_time = get_time()
            print(self.padding + 'start_time: {}'.format(string_utils.stringify_time(self.start_time)))

        self.current_count += 1

        if self.avoid_use_of_timer:
            if self.current_count - self.last_current_count >= self.print_interval or self.current_count==self.total_count:
                throughput = self.print_status()
                self.print_interval = throughput*30
        else:
            now = get_time()
            if now - self.last_operation_done_time > 30 or self.current_count==self.total_count:
                self.print_status()
                self.last_operation_done_time = now


    def finish(self):
        if self.start_time is not None:
            now = get_time()
            total_time = now - self.start_time
            print(self.padding + 'total_operations: {}'.format(self.current_count))
            print(self.padding + 'total_time: {} [{}]'.format(string_utils.stringify_time_delta(total_time), string_utils.stringify_time(now)))
        else:
            print(self.padding + 'finish')


