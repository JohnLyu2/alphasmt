import os
import logging 
import argparse
import json
import datetime

from alphasmt.AST import DerivationAST
from alphasmt.MCTS import MCTSNode, MCTS_RUN
from alphasmt.Environment import StrategyGame
from alphasmt.Evaluator import Z3StrategyEvaluator

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log_handler = logging.StreamHandler()
log_handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
log.addHandler(log_handler)

import functools
print = functools.partial(print, flush=True)

def main():
    log_folder = "experiments/results/out-{date:%Y-%m-%d_%H-%M-%S}/".format(date=datetime.datetime.now())
    assert(not os.path.exists(log_folder))
    os.makedirs(log_folder)
    parser = argparse.ArgumentParser()
    parser.add_argument('json_config', type=str, help='The experiment configuration file in json')
    configJsonPath = parser.parse_args()
    config = json.load(open(configJsonPath.json_config, 'r'))

    logic = config['logic']
    train_path = config['training_dir']
    val_path = config['validation_dir']
    num_val_strat = config['strategy_2b_validated']
    sim_num = config['simulation_number']
    timeout = config['timeout']
    batchSize = config['batch_size']

    # train
    log.info("MCTS Simulations Start")
    run = MCTS_RUN(sim_num, train_path, logic, timeout, batchSize, log_folder)
    run.start()
    strat_candidates = run.bestNStrategies(num_val_strat)
    log.info(f"Simulations done. {num_val_strat} strategies are selected.")

    # validate
    val_log = logging.getLogger("validation")
    val_log.setLevel(logging.INFO)
    vallog_handler = logging.FileHandler(f"{log_folder}/validation.log")
    val_log.addHandler(vallog_handler) 


    log.info("Validation Starts\n")
    valEvaluator = Z3StrategyEvaluator(val_path, timeout, batchSize)
    valSize = valEvaluator.getBenchmarkSize()
    bestPar2 = valSize * timeout * 2
    bestStrat = None
    for strat in strat_candidates:
      val_log.info(strat)
      val_log.info(f"Training Score: {run.getStrategyStat(strat)}")
      valResTuple = valEvaluator.evaluate(strat)  
      par2 = Z3StrategyEvaluator.caculateTimePar2(valResTuple, valSize, timeout)
      val_log.info(f"Validation: solved {valResTuple[0]} instances with rlimit {valResTuple[1]} and time {valResTuple[2]}; par2: {par2}\n")
      if par2 < bestPar2:
         bestPar2 = par2
         bestStrat = strat


    log.info(f"Best Strategy found: \n{bestStrat}")
    finalStratPath = f"{log_folder}/final_strategy.txt"
    with open(finalStratPath, 'w') as f:
       f.write(bestStrat)

if __name__ == "__main__":
    main()
