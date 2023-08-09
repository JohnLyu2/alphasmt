import pathlib
import threading
import subprocess
import shlex
import time

BATCH_SIZE = 2
TIME_OUT = 1  # sec

# copy from FastSMT


class Z3Runner(threading.Thread):
    """ Runner which executes a single strategy on a single formula by calling Z3 in shell"""

    def __init__(self, smt_file, timeout, id, strategy=None):
        threading.Thread.__init__(self)
        self.smt_file = smt_file
        self.timeout = timeout  # not used now
        self.strategy = strategy
        self.id = id

        if self.strategy is not None:
            self.new_file_name = f"./tmp/tmp_{id}.smt2"
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

        assert (not res.startswith('(error'))

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
    def __init__(self, benchmark_dir):
        self.benchmarkDir = benchmark_dir
        self.benchmarkLst = [str(p) for p in sorted(
            list(pathlib.Path(self.benchmarkDir).rglob(f"*.smt2")))]
        assert (len(self.benchmarkLst) > 0)

    def _par2Reward(self):  # to-do: add result check step
        assert (len(self.results) == len(self.benchmarkLst))
        maxPar2 = 2 * TIME_OUT * len(self.benchmarkLst)
        evalPar2 = 0
        for id in self.results:
            # to-do: also check for result correctness
            if self.results[id][0] == "sat" or self.results[id][0] == "unsat":
                evalPar2 += self.results[id][2]
            else:
                evalPar2 += TIME_OUT * 2
        return (maxPar2-evalPar2)/maxPar2

    def evaluate(self, strat_str):
        self.results = {}
        size = len(self.benchmarkLst)
        for i in range(0, size, BATCH_SIZE):
            batch_instance_ids = range(i, min(i+BATCH_SIZE, size))
            threads = []
            for id in batch_instance_ids:
                smtfile = self.benchmarkLst[id]
                runnerThread = Z3Runner(smtfile, TIME_OUT, id, strat_str)
                runnerThread.start()
                threads.append(runnerThread)
            time_start = time.time()
            for task in threads:
                time_left = max(0, TIME_OUT - (time.time() - time_start))
                task.join(time_left)
                id, resTask, rlimitTask, timeTask = task.collect()
                self.results[id] = (resTask, rlimitTask, timeTask)
        reward = self._par2Reward()
        return reward
