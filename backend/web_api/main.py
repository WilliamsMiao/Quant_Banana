"""
FastAPI主应用
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import uvicorn
import logging
from contextlib import asynccontextmanager

from .routes import auth, trading, strategies, backtesting, monitoring
from ..core.event_engine.event_manager import EventManager
from ..monitoring.health_check import HealthChecker

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量
event_manager = None
health_checker = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global event_manager, health_checker
    
    # 启动时初始化
    logger.info("启动量化交易系统...")
    
    # 初始化事件管理器
    event_manager = EventManager()
    await event_manager.start()
    
    # 初始化健康检查
    health_checker = HealthChecker()
    
    logger.info("系统启动完成")
    
    yield
    
    # 关闭时清理
    logger.info("关闭量化交易系统...")
    if event_manager:
        await event_manager.stop()
    logger.info("系统已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="量化交易系统API",
    description="基于Webull、富途和DeepSeek的智能量化交易系统",
    version="1.0.0",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 注册路由
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(trading.router, prefix="/api/trading", tags=["交易"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["策略"])
app.include_router(backtesting.router, prefix="/api/backtesting", tags=["回测"])
app.include_router(monitoring.router, prefix="/api/monitoring", tags=["监控"])


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "量化交易系统API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    if health_checker:
        return await health_checker.check_health()
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
