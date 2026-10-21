"""统一返回体：{ code, msg, data }

约定错误码（与 SRS 第 6 节一致）：
- 200 成功
- 400 参数 / 业务校验失败
- 401 未登录或 Token 失效
- 403 无权限
- 500 服务端异常
"""
from typing import Any


class Resp:
    @staticmethod
    def ok(data: Any = None, msg: str = "操作成功") -> dict:
        return {"code": 200, "msg": msg, "data": data}

    @staticmethod
    def fail(msg: str = "操作失败", code: int = 400, data: Any = None) -> dict:
        return {"code": code, "msg": msg, "data": data}

    @staticmethod
    def page(total: int, rows: list) -> dict:
        return Resp.ok({"total": total, "list": rows})
