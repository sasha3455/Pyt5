import os
import multiprocessing
import psutil
import logging
from datetime import datetime
import threading
import queue

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

def caesar_cipher(text, shift=3, encrypt=True):
    result = []
    for char in text:
        if char.isalpha():
            shift_dir = shift if encrypt else -shift
            if char.isupper():
                new_char = chr((ord(char) - ord('A') + shift_dir) % 26 + ord('A'))
            else:
                new_char = chr((ord(char) - ord('a') + shift_dir) % 26 + ord('a'))
            result.append(new_char)
        else:
            result.append(char)
    return ''.join(result)

def split_text(text, n):
    part_size = len(text) // n
    parts = [text[i*part_size : (i+1)*part_size] for i in range(n-1)]
    parts.append(text[(n-1)*part_size:])
    return parts

def save_part_result(filename, part, index, result_queue):
    try:
        temp_filename = f"{filename}.part{index}"
        with open(temp_filename, 'w') as f:
            f.write(part)
        result_queue.put((index, temp_filename))
        logger.info(f"Часть {index} сохранена во временный файл {temp_filename}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении части {index}: {e}")

def process_part(part, index, action, result_queue):
    logger.info(f"Обработка части {index} начата")
    
    save_queue = queue.Queue()
    
    if action == 'шифрование':
        processed_part = caesar_cipher(part, encrypt=True)
    else:
        processed_part = caesar_cipher(part, encrypt=False)
    
    save_thread = threading.Thread(
        target=save_part_result,
        args=(f"temp_{action}_part", processed_part, index, save_queue),
        daemon=True
    )
    save_thread.start()
    
    save_thread.join()
    
    result = save_queue.get()
    logger.info(f"Обработка части {index} завершена")
    return result

def combine_parts(output_file, parts_info):
    parts_info.sort(key=lambda x: x[0])
    
    with open(output_file, 'w') as outfile:
        for index, temp_file in parts_info:
            try:
                with open(temp_file, 'r') as infile:
                    outfile.write(infile.read())
                os.remove(temp_file)
                logger.info(f"Временный файл {temp_file} удален")
            except Exception as e:
                logger.error(f"Ошибка при объединении файла {temp_file}: {e}")

def get_max_processes():
    cpu_cores = os.cpu_count()
    cpu_percent = psutil.cpu_percent(interval=1)
    available_percent = 100 - cpu_percent
    max_processes = int(cpu_cores * (available_percent / 100))
    return max(1, min(cpu_cores, max_processes))

def main():
    print("Файловый шифратор/дешифратор")
    print("----------------------------")
    
    while True:
        action = input("Выберите действие (шифрование/дешифрование): ").lower()
        if action in ['шифрование', 'дешифрование']:
            break
        print("Некорректный ввод. Попробуйте снова.")
    
    while True:
        input_file = input("Введите путь к файлу: ")
        if os.path.exists(input_file):
            if os.path.isfile(input_file):
                break
            else:
                print("Указанный путь ведет к директории, а не к файлу. Пожалуйста, введите путь к файлу.")
        else:
            print("Файл не найден. Пожалуйста, введите корректный путь к файлу.")
    
    with open(input_file, 'r') as f:
        text = f.read()
    
    max_processes = get_max_processes()
    print(f"Доступно процессов: {max_processes} (ядер: {os.cpu_count()}, загрузка CPU: {psutil.cpu_percent()}%)")
    
    while True:
        try:
            num_processes = int(input(f"Введите количество процессов (1-{max_processes}): "))
            if 1 <= num_processes <= max_processes:
                break
            print(f"Число должно быть от 1 до {max_processes}")
        except ValueError:
            print("Некорректный ввод. Попробуйте снова.")
    
    parts = split_text(text, num_processes)
    
    manager = multiprocessing.Manager()
    result_queue = manager.Queue()
    
    pool = multiprocessing.Pool(processes=num_processes)
    
    logger.info("Начало обработки файла")
    start_time = datetime.now()
    
    results = []
    for i, part in enumerate(parts):
        results.append(pool.apply_async(process_part, args=(part, i, action, result_queue)))
    
    pool.close()
    pool.join()
    
    parts_info = []
    for res in results:
        parts_info.append(res.get())
    
    output_file = f"{input_file}.{'enc' if action == 'шифрование' else 'dec'}"
    combine_parts(output_file, parts_info)
    
    end_time = datetime.now()
    logger.info(f"Обработка завершена за {(end_time - start_time).total_seconds():.2f} секунд")
    print(f"Результат сохранен в файл: {output_file}")

if __name__ == '__main__':
    main()