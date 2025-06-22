from fastapi import HTTPException
from fastapi.responses import JSONResponse

from datetime import datetime, timezone
from src.database import models
import sys
import traceback
from . import utils
import pytz, sys

AMSP = pytz.timezone('America/Sao_Paulo')

def handle_error(error, function):
    utc_dt = datetime.now(timezone.utc)
    dataErro = utc_dt.astimezone(AMSP)
    exc_type, exc_value, exc_traceback = sys.exc_info()
    filename = exc_traceback.tb_frame.f_code.co_filename
    line_no = exc_traceback.tb_lineno
    utils.grava_error_arquivo({"error": f"""{traceback.format_exc()}""","data": str(dataErro)})
    raise HTTPException(status_code=500, detail=f"Error in function {function.__name__} at {filename}:{line_no}: {str(error)}")