# \web开发\FastAPI\FastAPI入门.py
# 导入FastAPI
import os.path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import JSONResponse

import service as se
import logging

# 日志记录 为了能够灵活控制项目中日志的输出，我们可以使用logging模块输出日志
# 日志级别就是给日志记录器设置日志级别，日志级别有5种：DEBUG、INFO、WARNING、ERROR、CRITICAL
# 配置日志的基本信息
logging.basicConfig(
    level=logging.ERROR, # 日志级别
    # %(asctime)s： 时间 %(name)s： 日志记录器的名字 %(levelname)s：日志级别 %(fliename)s:%(lineno)d：文件名 行数 %(message)s： 日志信息
    format="%(asctime)s - %(name)s - %(levelname)s  - %(filename)s:%(lineno)d - %(message)s" # 日志格式
)



# 创建FastAPI实例
app = FastAPI(title="汉字谜盒")

# 只定义index.html无法找到css和js 没有函数处理css和js路径 ---->挂载静态文件资源存放目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# 创建会话所存放的目录 sessions
if not os.path.exists("sessions"):
    # 创建目录
    os.mkdir("sessions")

# 定义路径操作函数
@app.get("/")
def root():
    """
    访问项目首页
    """
    logging.info("访问项目首页")
    return FileResponse("static/index.html")# 返回的是一个页面

# 新建会话：在打开项目页面的时候 之前没有会话 则要自动创建一个会话 会话标识形如 2026-4-15_12-00-05
@app.post("/api/sessions")
def create_seesion():
    return se.create_session()


# AI交互接口
# 接受请求参数
@app.post("/api/chat")
def chat(request:se.ChatRequest):# 通过对象来接受参数
    ai_reply = se.AIchat(request.session_id,request.message)
    return se.APIResponse(code=200,message="请求成功",data=ai_reply)


# 会话列表接口
@app.get("/api/sessions")
def get_session_list():
    return se.session_list()


# 加载会话接口
@app.get("/api/sessions/{session_id}") # {session_id}是动态的参数
def load_session(session_id):
    return se.load_session(session_id)


# 删除会话接口
@app.delete("/api/sessions/{session_id}")
def delete_session(session_id):
    return se.delete_seesion(session_id)



# 统一处理异常---->返回对象类型得是Response
@app.exception_handler(Exception)
def handle_exception(request, exc: Exception):
    logging.error(f"处理异常，请求路径：{request.url}，异常信息：{exc}")
    return JSONResponse(content={"code": 500, "message": "服务器异常内部错误，请联系管理员~", "data": None})

# 运行FastAPI
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) # access_log=False 关闭日志