'''
Redis数据管理模块
封装所有Redis操作，提供简洁的接口业务层调用
'''
import redis
import json
from typing import List,Dict,Optional


# 创建radis类
class RedisManager:
    '''Redis 数据管理器'''
    def __init__(self, host="localhost", port=6379, db=0):
        '''
        初始化 Redis 连接
        :param host: Radis服务器地址
        :param port: radis 端口
        :param db: 使用的数据库编号
        '''
        self.redis_client = redis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True # 默认是False，返回字节，True返回字符串
        )

        # 测试连接是否正常
        try:
            self.redis_client.ping()
            print("✓ Redis 连接成功")
        except redis.ConnectionError as e:
            print(f"✗ Redis 连接失败: {e}")
            raise

    def create_session(self,session_id:str,session_data:dict):
        '''
        创建新会话
        :param session_id: 会话id
        :param session_data: 会话数据字典
        :return: 是否创建成功
        '''

        try:
            # 将消息列表转为JSON字符串
            data_to_store = {
                "current_session":session_data["current_session"],
                "messages":json.dumps(session_data["messages"])
            }

            # 将数据存储到Redis中
            self.redis_client.hset(f"session:{session_id}",mapping=data_to_store)

            # 设置24小时过期时间
            self.redis_client.expire(f"session:{session_id}",86400)

            # 添加到会话列表
            self.redis_client.lpush("session_list",session_id)

            return  True
        except Exception as e:
            print(f"创建会话失败: {e}")
            return False


    def get_session(self,session_id:str)->Optional[dict]:
        '''
        获取指定会话数据
        :param session_id: 会话id
        :return: 会话数据字典 不存在返回None
        '''
        try:
            # 获取会话数据
            session_data = self.redis_client.hgetall(f"session:{session_id}")

            # 如果不存在，返回None
            if not session_data:
                return None

            # 将消息列表从JSON字符串转为列表
            session_data["messages"] = json.loads(session_data["messages"])

            return session_data
        except Exception as e:
            print(f"获取会话失败: {e}")
            return None


    def update_session_messages(self, session_id: str, messages: list) -> bool:
        """
        更新会话的消息列表

        参数:
            session_id: 会话ID
            messages: 消息列表

        返回:
            bool: 是否更新成功
        """
        try:
            # 将消息列表转为JSON字符串
            self.redis_client.hset(
                f"session:{session_id}",
                "messages",
                json.dumps(messages)
            )

            # 刷新过期时间
            self.redis_client.expire(f"session:{session_id}", 86400)

            return True
        except Exception as e:
            print(f"更新会话失败: {e}")
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        删除指定会话

        参数:
            session_id: 会话ID

        返回:
            bool: 是否删除成功
        """
        try:
            # 删除会话数据
            self.redis_client.delete(f"session:{session_id}")

            # 从会话列表中移除
            self.redis_client.lrem("session_list", 0, session_id)

            return True
        except Exception as e:
            print(f"删除会话失败: {e}")
            return False

    def get_all_sessions(self) -> List[str]:
        """
        获取所有会话ID列表

        返回:
            list: 会话ID列表
        """
        try:
            # 获取整个列表
            return self.redis_client.lrange("session_list", 0, -1)
        except Exception as e:
            print(f"获取会话列表失败: {e}")
            return []

    def session_exists(self, session_id: str) -> bool:
        """
        检查会话是否存在

        参数:
            session_id: 会话ID

        返回:
            bool: 是否存在
        """
        try:
            return self.redis_client.exists(f"session:{session_id}") > 0
        except Exception as e:
            print(f"检查会话存在性失败: {e}")
            return False

# 创建全局单例（整个应用共享一个Redis连接）
redis_manager = RedisManager()