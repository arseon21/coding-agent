import os
import sys
import logging
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.append(project_root)

from src.core.llm_client import LLMClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

def test_yandex_connection():
    load_dotenv()
    
    print("\n Проверка связи с YandexGPT")
    
    try:
        client = LLMClient()
        
        test_prompt = "Напиши на Python функцию, которая вычисляет числа Фибоначчи."
        print(f"Запрос: {test_prompt}\n")
        
        response = client.get_response(test_prompt)
        
        print("--- Ответ модели ---")
        print(response)
        print("--------------------")
        
        if response and len(response) > 10:
            print("\nТест пройден")
        else:
            print("\nПолучен пустой или слишком короткий ответ.")

    except Exception as e:
        print(f"\n Тест провалился с ошибкой:")
        print(f"Тип ошибки: {type(e).__name__}")
        print(f"Сообщение: {str(e)}")

if __name__ == "__main__":
    test_yandex_connection()