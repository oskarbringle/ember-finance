from pydantic import BaseModel


class ImportCommit(BaseModel):
    replace_current_data: bool = True
