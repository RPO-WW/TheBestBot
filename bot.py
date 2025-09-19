from loguru import logger
import logging

class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Получаем соответствующий уровень loguru
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        
        # Находим вызывающий объект для отслеживания
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

def build_application(token: str):
    # Перехватываем логирование стандартной библиотеки
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    
    # Ваша существующая логика создания приложения
    application = Application.builder().token(token).build()
    
    # Настройка handlers и т.д.
    return application
