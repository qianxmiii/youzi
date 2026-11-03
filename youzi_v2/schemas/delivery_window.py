from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DeliveryWindowIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: Literal['auto', 'range', 'amazon'] = 'auto'
    manual_start: date | None = Field(default=None, alias='manualStart')
    manual_end: date | None = Field(default=None, alias='manualEnd')

    @model_validator(mode='after')
    def check_range(self):
        if (self.manual_start is None) != (self.manual_end is None):
            raise ValueError('人工窗口开始和结束日期必须同时填写')
        if self.manual_start and self.manual_end < self.manual_start:
            raise ValueError('结束日期不能早于开始日期')
        return self

