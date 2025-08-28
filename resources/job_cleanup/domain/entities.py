from typing import Optional

from pydantic import BaseModel


class Item(BaseModel):
    id: str
    name: Optional[str] = None