# main.py
# 依赖安装: pip install fastapi uvicorn python-multipart
# 启动命令: uvicorn main:app --reload
# 接口文档: http://127.0.0.1:8000/docs

import uuid
import datetime
from typing import Annotated, Optional

from fastapi import FastAPI, Path, Query, Header, Form, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(title="FastAPI Mini Demo", version="1.0.0")


# ────────────────────────────────────────────
# 公共输出结构（演示多种 Python 类型的输出转换）
# ────────────────────────────────────────────
class ResultModel(BaseModel):
    request_id: uuid.UUID = Field(default_factory=uuid.uuid4)  # UUID   → JSON 字符串
    timestamp: datetime.datetime = Field(                        # datetime → ISO 8601
        default_factory=datetime.datetime.utcnow
    )
    path_param: str                          # str
    query_int: int                           # int
    query_float: float                       # float
    query_bool: bool                         # bool
    query_tags: list[str]                    # list
    header_lang: Optional[str]              # Optional str（可为 null）
    extra: Optional[dict] = None            # dict / null


# ════════════════════════════════════════════
# GET /items/{item_name}
# 覆盖：路径参数 · 查询参数 · Headers · 多类型输出转换
# ════════════════════════════════════════════
@app.get("/items/{item_name}", response_model=ResultModel, tags=["Items"])
def get_item(
    # ① 路径参数（str，自动校验非空）
    item_name: Annotated[str, Path(min_length=1, max_length=50, description="物品名称")],

    # ② 查询参数（多类型，含校验）
    count:  Annotated[int,   Query(ge=1, le=1000, description="数量 1~1000")]  = 1,
    price:  Annotated[float, Query(ge=0.0,        description="单价 ≥ 0")]     = 9.9,
    in_stock: Annotated[bool, Query(description="是否在库")] = True,
    tags: Annotated[list[str], Query(description="标签列表，可多次传入")] = [],

    # ③ Header 参数
    accept_language: Annotated[Optional[str], Header(description="语言偏好，如 zh-CN")] = None,
    x_request_id:   Annotated[Optional[str], Header(description="调用方追踪 ID")]       = None,
):
    """
    **输入来源：**
    - `item_name` → 路径参数，str
    - `count / price / in_stock / tags` → 查询参数，自动转换为 int / float / bool / list
    - `Accept-Language / X-Request-Id` → HTTP Header

    **输出转换：**
    - `request_id`（UUID）、`timestamp`（datetime）→ JSON 字符串
    - `query_int / float / bool / list` → JSON 原生类型
    """
    result = ResultModel(
        path_param=item_name,
        query_int=count,
        query_float=round(price * count, 4),   # 计算总价，float 输出
        query_bool=in_stock,
        query_tags=tags,
        header_lang=accept_language,
        extra={"caller_id": x_request_id},     # dict 输出
    )

    # 构造响应头：将调用方 ID 回传
    headers = {"X-Request-ID": x_request_id} if x_request_id else {}
    return JSONResponse(content=result.model_dump(mode="json"), headers=headers)


# ════════════════════════════════════════════
# POST /items/{item_name}/order
# 覆盖：路径参数 · 查询参数 · Headers · Form 表单 · 多类型输出转换
# ════════════════════════════════════════════
@app.post("/items/{item_name}/order", response_model=ResultModel, tags=["Items"])
def create_order(
    # ① 路径参数
    item_name: Annotated[str, Path(min_length=1, max_length=50, description="物品名称")],

    # ② 查询参数（订单优先级、是否加急）
    priority: Annotated[int,  Query(ge=1, le=5, description="优先级 1~5")] = 3,
    urgent:   Annotated[bool, Query(description="是否加急")]               = False,

    # ③ Header
    x_api_key:  Annotated[str,           Header(description="API 密钥，必填")] = ...,
    x_client_id: Annotated[Optional[str], Header(description="客户端 ID")]     = None,

    # ④ Form 表单字段（multipart/form-data 或 application/x-www-form-urlencoded）
    buyer:    Annotated[str,   Form(min_length=2, max_length=30, description="买家姓名")] = ...,
    quantity: Annotated[int,   Form(ge=1, le=999, description="购买数量")]                = ...,
    discount: Annotated[float, Form(ge=0.0, le=1.0, description="折扣率 0~1")]            = 1.0,
    note:     Annotated[Optional[str], Form(max_length=200, description="备注")]          = None,
):
    """
    **输入来源（全部合并在本接口）：**
    - `item_name` → 路径参数，str
    - `priority / urgent` → 查询参数，int / bool
    - `X-Api-Key / X-Client-Id` → HTTP Header（key 必传，否则 422）
    - `buyer / quantity / discount / note` → Form 表单，str / int / float / Optional[str]

    **输出转换：** 同 GET 接口（UUID、datetime、多种基础类型 → JSON）
    """
    # 简单鉴权演示（Header 校验）
    if x_api_key != "demo-secret":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-Api-Key 无效，请使用 'demo-secret'",
        )

    final_price = round(9.9 * quantity * discount, 4)

    result = ResultModel(
        path_param=item_name,
        query_int=priority,          # int
        query_float=final_price,     # float：数量 × 折扣后总价
        query_bool=urgent,           # bool
        query_tags=[buyer],          # list
        header_lang=x_client_id,
        extra={                      # dict：汇总订单信息
            "buyer": buyer,          # str
            "quantity": quantity,    # int
            "discount": discount,    # float
            "note": note,            # Optional[str] → str or null
            "urgent": urgent,        # bool
        },
    )
    return result