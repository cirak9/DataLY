from pydantic import BaseModel


class KeywordOut(BaseModel):
    id: int
    keyword: str
    is_whole_word: bool

    model_config = {"from_attributes": True}


class CategoryOut(BaseModel):
    id: int
    main: str
    sub: str
    keywords: list[KeywordOut]

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    main: str
    sub: str


class KeywordCreate(BaseModel):
    keyword: str
    is_whole_word: bool = False
