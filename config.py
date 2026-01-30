from dataclasses import dataclass
from typing import List

@dataclass
class Config:
    BOT_TOKEN: str = "8287955993:AAGyLyXHCSheM4EUYI_20L2caMVxjp-jv2Q"
    ADMIN_IDS: List[int] = None
    
    # Рабочие часы
    WORK_START: int = 9   # с 9:00
    WORK_END: int = 21    # до 21:00
    SLOT_DURATION: int = 60  # минут на запись
    
    # Дней для записи вперёд
    DAYS_AHEAD: int = 14
    
    def __post_init__(self):
        if self.ADMIN_IDS is None:
            self.ADMIN_IDS = [8466698088]  # Твой Telegram ID

config = Config()
