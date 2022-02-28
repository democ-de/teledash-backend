from datetime import datetime
from typing import List, Optional, Union

from pydantic import BaseModel


class AggregatedMetrics(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    time_delta: Optional[int] = None  # TODO: improve by using datetime.timedelta
    sum: Optional[int] = None
    diff: Optional[int] = None
    data: Optional[List[Union[int, None]]] = None
