from pydantic import BaseModel, ConfigDict, Field


class WecomWebhookTestBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    content: str | None = Field(
        default=None,
        description="测试消息正文，默认「Youzi 企业微信机器人连通测试」",
    )


class WecomWebhookTestResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ok: bool
    errcode: int
    errmsg: str
