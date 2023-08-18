import pathlib
import threading
import subprocess
import shlex
import time
import logging

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
log.addHandler(log_handler)

class Z3Runner(threading.Thread):
    """ Runner which executes a single strategy on a single formula by calling Z3 in shell"""
    def __init__(self, smt_file, timeout, id, strategy=None):
        threading.Thread.__init__(self)
        self.smt_file = smt_file
        self.timeout = timeout  # not used now
        self.strategy = strategy
        self.id = id

        if self.strategy is not None:
            self.new_file_name = f"/tmp/tmp_{id}.smt2"
            self.tmp_file = open(self.new_file_name, 'w')
            with open(self.smt_file, 'r') as f:
                for line in f:
                    new_line = line
                    if 'check-sat' in line:
                        new_line = f"(check-sat-using {strategy})\n"
                    self.tmp_file.write(new_line)
            self.tmp_file.close()
        else:
            self.new_file_name = self.smt_file

    def run(self):
        self.time_before = time.time()
        z3_cmd = 'z3 -smt2 %s -st' % self.new_file_name
        self.p = subprocess.Popen(shlex.split(z3_cmd), stdout=subprocess.PIPE)
        self.p.wait()
        self.time_after = time.time()

    def collect(self):
        if self.is_alive():
            try:
                self.p.terminate()
                self.join()
            except OSError:
                pass
            return self.id, None, None, None

        out, err = self.p.communicate()

        lines = out[:-1].decode("utf-8").split('\n')
        res = lines[0]

        if res.startswith('(error'):
            log.warn(f"Invalid strategy: {self.strategy}\n{res}")
            return self.id, None, None, None

        rlimit = None
        for line in lines:
            if 'rlimit' in line:
                tokens = line.split(' ')
                for token in tokens:
                    if token.isdigit():
                        rlimit = int(token)

        if res == 'unknown':
            res = None

        return self.id, res, rlimit, self.time_after - self.time_before

class Z3StrategyEvaluator():
    def __init__(self, benchmark_dir, timeout, batch_size):
        self.benchmarkDir = benchmark_dir
        self.benchmarkLst = [str(p) for p in sorted(
            list(pathlib.Path(self.benchmarkDir).rglob(f"*.smt2")))]
        assert (self.getBenchmarkSize() > 0)
        self.timeout = int(timeout / 10) # now for testing
        self.batchSize = batch_size
    
    def getBenchmarkSize(self):
        return len(self.benchmarkLst)

    # returns a tuple (#solved, total rlimit, total time)
    def evaluate(self, strat_str):
        results = {}
        numSolved = 0
        rlimitSolved = 0
        timeSolved = 0
        size = self.getBenchmarkSize()
        for i in range(0, size, self.batchSize):
            batch_instance_ids = range(i, min(i+self.batchSize, size))
            threads = []
            for id in batch_instance_ids:
                smtfile = self.benchmarkLst[id]
                runnerThread = Z3Runner(smtfile, self.timeout, id, strat_str)
                runnerThread.start()
                threads.append(runnerThread)
            time_start = time.time()
            for task in threads:
                time_left = max(0, self.timeout - (time.time() - time_start))
                task.join(time_left)
                id, resTask, rlimitTask, timeTask = task.collect()
                results[id] = (resTask, rlimitTask, timeTask)
        assert len(results) == size
        for id in results:
            # to-do: also check for result correctness
            if results[id][0] == "sat" or results[id][0] == "unsat":
                numSolved += 1
                rlimitSolved += results[id][1]
                timeSolved += results[id][2]
        return (numSolved, rlimitSolved, timeSolved)
    
    @staticmethod
    def caculateTimePar2(res_tuple, total_instnace, timeout):
        numSolved, rlimitSum, timeSum = res_tuple
        numUnsolved = total_instnace - numSolved
        return timeSum + numUnsolved * timeout * 2

    # add argument to select type of reward; now scaled time par2
    def getReward(self, strat_str):
        res_tuple = self.evaluate(strat_str)
        size = self.getBenchmarkSize()
        par2 = Z3StrategyEvaluator.caculateTimePar2(res_tuple, size, self.timeout)
        maxPar2 = 2 * self.timeout * size
        return float(maxPar2-par2)/maxPar2
