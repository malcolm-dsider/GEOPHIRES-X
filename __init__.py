"""
import traceback
import logging
#get logging started
logging.config.fileConfig('logging.conf')
global logger
logger = logging.getLogger('root')


#handle exception logging
def log_traceback(ex, ex_traceback=None) -> None:
    if ex_traceback is None:
        ex_traceback = ex.__traceback__
    tb_lines = [ line.rstrip('\n') for line in
                 traceback.format_exception(ex.__class__, ex, ex_traceback)]
    logger.critical(tb_lines)
"""
