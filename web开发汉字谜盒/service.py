import json
from datetime import datetime
import os
from typing import Any
from openai import OpenAI
from pydantic import BaseModel

# 导入Redis管理器
from redis_manager import redis_manager
import logging

# 日志记录 为了能够灵活控制项目中日志的输出，我们可以使用logging模块输出日志
# 日志级别就是给日志记录器设置日志级别，日志级别有5种：DEBUG、INFO、WARNING、ERROR、CRITICAL
# 配置日志的基本信息
logging.basicConfig(
    level=logging.INFO, # 日志级别
    # %(asctime)s： 时间 %(name)s： 日志记录器的名字 %(levelname)s：日志级别 %(fliename)s:%(lineno)d：文件名 行数 %(message)s： 日志信息
    format="%(asctime)s - %(name)s - %(levelname)s  - %(filename)s:%(lineno)d - %(message)s" # 日志格式
)

def generate_session_id(): # 生成会话标识
    return datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

# BaseModel：是Pydantic库提供的父类（FastAPI深度集成了Pydantic，用于定义FastAPI数据模型和数据验证的规则）
class APIResponse(BaseModel):# 返回的 数据模型
    code: int
    message: str
    data: Any # 任意类型的数据

class ChatRequest(BaseModel): # 接收的 数据模型
    session_id: str
    message: str


# 创建与AI大模型交互的客户端对象（DEEPSEEK_API_KEY环境变量的名字，值就是Deeepseek的api key）
client = OpenAI(
    api_key=os.environ.get('DEEPSEEK_API_KEY'),
    base_url="https://api.deepseek.com")

# 定义系统提示词
SYSTEM_PROMPT = """
# 角色定义
你是一个专门玩猜字谜的AI小助手，只进行字谜互动，不闲聊无关内容，全程纯文本交互，不使用表情符号。

## 核心能力
- 出字谜、判对错、给提示
- 记忆已用谜题，确保会话内不重复
- 简洁明快回应

## 出题规则（严格执行！）
1. 开场先友好打招呼，并随机出一道常见、简单、适合大众并必须符合逻辑推理的字谜，禁止使用生僻、低俗、网络烂梗。
2. 题目格式：“谜面”（打一字）。
3. 每次出题必须完全随机，禁止重复使用相同题目，也可以偶尔穿插使用，下面示例中的谜语。
4. 新出题目时, 不要提示, 用户需要提示时, 或者答错时, 再给予合理的提示。

## 判题规则（严格执行！）
1. 用户只回复一个字时，直接视为答案。
2. 答对：立即夸奖并揭晓谜底，格式如“太棒了！就是‘X’字！要不要再来一题？”
3. 答错：告知不对，可给一句简短提示，但不泄露答案。格式如“不对哦，再想想~”
4. 严禁在用户答错后直接公布答案！只有用户说“公布答案”或“不知道”等情况时才公布。

## 互动流程
1. 用户答对：夸奖 + 确认正确 + 询问“要不要再来一题？”
2. 用户答错：告知不对 + 简单提示 + 鼓励继续猜
3. 用户说“提示一下”：给出简短线索，不公布答案
4. 用户说“公布答案”或“不知道”：揭晓谜底并解释 + 询问“要不要再来一题？”
5. 用户说“换一题”“再来一题”：立即更换新字谜

## 回复风格约束
- 语气轻松有趣，但保持简洁
- 全程只围绕字谜，拒绝回答其他问题
- 回复不超过3句话
- **绝对不要在回复中说“这个出过了，我来个新的”或类似表述** — 直接给出新谜语即可
- 判题错误零容忍，不确定谜底时，先回复“我再想想”而不是乱判

## 常见谜语类型及谜底参考示例, 仅仅为参照示例
### 组合类
- 「一加一不是二」= 王
- 「二人不是天」= 夫
- 「十口不是田」= 古

### 包含类
- 「一人在内」= 肉
- 「口里有人」= 囚
- 「门里有口」= 问
- 「田里长草」= 苗
- 「心里有你」= 您
- 「山里有山」= 出
- 「王头上有人」= 全
- 「水上有石」= 泵

### 半取类
- 「半吃半拿」= 哈
- 「半真半假」= 值
- 「半青半紫」= 素
- 「半朋半友」= 有
- 「半推半就」= 扰
- 「半山半水」= 汕

### 象形类
- 「三人又重逢」= 众
- 「一口咬掉牛尾巴」= 告
- 「两座山」= 出
- 「三日又重逢」= 晶
"""

# 根据session_id获取文件名
def get_session_file_name(session_id):
    return os.path.join("sessions",session_id + ".json")

# 新建会话
def create_session():
    logging.info('创建会话')
    # 生成会话标识（会话名字）
    session_id = generate_session_id()

    # 组装会话信息，保存文件
    session_data = {
        "current_session": session_id,
        "messages": []
    }
    # # 将这个数据保存到文件当中
    # with open(os.path.join("sessions", session_id + ".json"), "w") as f:  # 创建文件
    #     json.dump(session_data, f, ensure_ascii=False, indent=2)  # 将数据写入文件

    # 使用Redis管理器保存数据
    success = redis_manager.create_session(session_id, session_data)

    if not success:
        return APIResponse(code=500, message="创建会话失败", data=None)

    # 返回数据
    # return {"code":200,"message":"创建会话成功","data":session_id}
    return APIResponse(code=200, message="创建会话成功", data=session_id)


# AI大模型交互---->逻辑实现
def AIchat(id,message):
    logging.info(f"AI交互接口{id} : {message}")

    # # 加载json文件的会话数据
    # session_path = get_session_file_name(id)
    # with open(session_path,"r",encoding="utf-8") as f:
    #     session_data = json.load(f)

    # 从Redis读取会话数据
    session_data = redis_manager.get_session(id)

    # 检查会话是否存在
    if not session_data:
        raise ValueError(f"会话 {id} 不存在")

    # 获取消息列表
    messages_list = session_data["messages"]

    # 构建AI大模型交互的消息数据
    messages = [
        {"role":"system","content":SYSTEM_PROMPT}
    ]
    # for message in session_data["messages"]: # 遍历会话数据中的消息
    #     messages.append(message)
    messages.extend(messages_list)  # 使用 extend 替代循环
    messages.append({"role":"user","content":message})

    # 调用Deepseek大模型
    # 与AI大模型进行交互
    logging.info(f"------------->调用ai大模型，提示词：", {message})
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages ,
        stream=False,
        temperature=1.5 , # 随机性 多样性
    )

    # 获取响应的数据
    ai_response = response.choices[0].message.content
    logging.info(f"------------->ai大模型响应数据：", {ai_response})

    # 更新消息列表中的消息
    # 添加ai反应回来的消息
    # session_data["messages"].append({"role": "user", "content": message})
    # session_data["messages"].append({"role": "assistant", "content": ai_response})
    # 更新消息列表 - 添加用户消息和AI回复
    messages_list.append({"role": "user", "content": message})
    messages_list.append({"role": "assistant", "content": ai_response})

    # 使用Redis管理器保存
    redis_manager.update_session_messages(id, messages_list) #

    logging.info(f"------------->更新会话数据：{session_data}")

    # # 保存会话消息到json文件中
    # with open(session_path,"w",encoding="utf-8") as f:
    #     json.dump(session_data,f,ensure_ascii=False,indent=2)

    return ai_response


# 获取会话列表---->逻辑实现
def session_list():
    logging.info("获取会话列表")
    # 获取sessions目录下的所有文件名
    # sessions_files = os.listdir("sessions")
    # session_list = [flie.split(".")[0] for flie in sessions_files]

    # 使用Redis管理器获取会话列表
    session_list = redis_manager.get_all_sessions()
    logging.info(f"------------->获取的会话列表：{session_list}")

    # # 让列表倒序
    # session_list.sort(reverse=True)
    return APIResponse(code=200,message="获取会话列表成功",data=session_list)


# 获取指定会话信息
def load_session(id):
    logging.info("加载指定会话")
    # # 获取文件会话名
    # session_path = get_session_file_name(id)

    # 使用Redis管理器获取会话数据
    session_data = redis_manager.get_session(id)

    # 检查会话是否存在
    if not session_data:
        return APIResponse(code=404, message="会话不存在", data=None)

    # # 读取会话文件
    # with open(session_path,"r",encoding="utf-8") as f:
    #     session_data = json.load(f)

    # 返回会话数据
    return APIResponse(code=200,message="获取会话成功",data=session_data)


# 删除会话逻辑实现
def delete_seesion(id):
    logging.info("删除指定会话")
    # session_path = get_session_file_name(id) # 获取文件会话名

    if redis_manager.get_session(id):
        # 使用Redis管理器删除会话
        success = redis_manager.delete_session(id)

        if success:
            logging.info("------------->删除的会话：%s", id)
            return APIResponse(code=200, message="删除会话成功", data=None)
        else:
            return APIResponse(code=500, message="删除会话失败", data=None)
    else:
        return APIResponse(code=404, message="会话不存在", data=None)

    # if os.path.exists(session_path): # 如果存在这个文件
    #     logging.info("------------->删除的会话文件：", {session_path})
    #     os.remove(session_path)
    #     return APIResponse(code=200,message="删除会话成功",data=None)
    # else:
    #     return APIResponse(code=500,message="删除会话失败",data=None)