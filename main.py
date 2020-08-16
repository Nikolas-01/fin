# импорты необходимых библиотек
import requests
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
import matplotlib.image as mpimg
from sklearn.utils import shuffle


# класс обработчика-бота
class BotHandler:
    def __init__(self, token):
        '''
        Инициализация необходимых параметров
        :param token: токен бота
        '''
        self.token = token
        self.api_url = "https://api.telegram.org/bot{}/".format(token)

    def get_updates(self, offset=None, timeout=30):
        '''
        Мониторинг присланных сообщений
        :return: результат обнаруженных обновлений/присланных сообщений
        '''
        method = 'getUpdates'
        params = {'timeout': timeout, 'offset': offset}
        resp = requests.get(self.api_url + method, params)
        result_json = resp.json()['result']
        return result_json

    def send_message(self, chat_id, text):
        '''
        Метод отправки сообщения
        :param chat_id: id чата для отправки
        :param text: текст сообщения
        :return: response сервера
        '''
        params = {'chat_id': chat_id, 'text': text}
        method = 'sendMessage'
        resp = requests.post(self.api_url + method, params)
        return resp

    def get_last_update(self):
        '''
        Получение последнего обновления
        :return: последнее обновление
        '''
        get_result = self.get_updates()

        if len(get_result) > 0:
            last_update = get_result[-1]
        else:
            last_update = get_result[len(get_result)]

        return last_update

    def load_photo(self, last_chat_file_id):
        '''
        Получение/загрузка фотографии, присланного пользователем бота
        :param last_chat_file_id: id чата присланной фотографии
        :return: -
        '''

        # получаем путь к картинке
        method = 'getFile'
        image_name = 'initial.jpg'
        data = {"file_id": last_chat_file_id}
        ret = requests.post(self.api_url + method, data=data)

        # загружаем на сервер картинку
        data = {'file_path': ret.json()['result']['file_path']}
        ret = requests.get('https://api.telegram.org/file/bot{}/{}'.format(self.token, data['file_path']))
        if ret.status_code == 200:
            with open(image_name, 'wb') as f:
                f.write(ret.content)

    def build_new_img(self, chat_id, last_chat_caption):
        '''
        Создание кластеризованного изображения
        :param chat_id: чат id для отправки собранного изображения
        :param last_chat_caption: кол-во цветов для кластеризации
        :return: -
        '''

        method = 'sendPhoto'
        image_path = 'built_img.png'
        data = {"chat_id": chat_id, "caption": 'Обработанная фотография'}

        # количество цветов для конвертации
        n_colors = int(last_chat_caption)

        # загрузка изображения
        initial_img = mpimg.imread('initial.jpg')

        # конвертация значений в диапазон [0, 1)
        initial_img = np.array(initial_img, dtype=np.float64) / 255

        # трансформация в 2d массив изображения
        w, h, d = original_shape = tuple(initial_img.shape)
        assert d == 3
        image_array = np.reshape(initial_img, (w * h, d))

        # кластеризация изображения по случайный 1000 точкам
        image_array_sample = shuffle(image_array, random_state=0)[:1000]
        kmeans = KMeans(n_clusters=n_colors, random_state=0).fit(image_array_sample)
        labels = kmeans.predict(image_array)

        # функция сборки кластеризованных пикселей в 'исходное' изображение
        def recreate_image(codebook, labels, w, h):
            d = codebook.shape[1]
            image = np.zeros((w, h, d))
            label_idx = 0
            for i in range(w):
                for j in range(h):
                    image[i][j] = codebook[labels[label_idx]]
                    label_idx += 1
            return image

        # сохранение кластеризованного фото
        plt.imsave('built_img.png', recreate_image(kmeans.cluster_centers_, labels, w, h))

        # отправки готового изображения
        with open(image_path, "rb") as image_file:
            ret = requests.post(self.api_url + method, data=data, files={"photo": image_file})


# создание бота
token = 'ВАШ_ТОКЕН_СЮДА ВСТАВИТЬ (КАВЫЧКИ НЕ УБИРАТЬ)'
greet_bot = BotHandler(token)


# функция-слушатель запросов для бота
def main():
    new_offset = None

    while True:
        # получаем обновленные данные
        greet_bot.get_updates(new_offset)

        last_update = greet_bot.get_last_update()

        last_chat_caption = ''
        last_chat_file_id = ''
        try:
            last_chat_caption = last_update['message']['caption']
            last_chat_file_id = last_update['message']['photo'][len(last_update['message']['photo'])-1]['file_id']
        except Exception:
            pass

        last_update_id = last_update['update_id']

        last_chat_text = ''
        try:
            last_chat_text = last_update['message']['text']
        except Exception:
            pass

        last_chat_id = last_update['message']['chat']['id']
        last_chat_name = last_update['message']['chat']['first_name']

        # на основе присланного сообщения отвечаем соответствующе
        if last_chat_text == '/start':
            greet_bot.send_message(last_chat_id, 'Привет, {}. Пришли мне любую фотографию в формате jpg'
                                                 ', указав в описании целое неотрицательное число '
                                                 '- количество цветов в новом изображении'.format(last_chat_name))
        else:
            greet_bot.load_photo(last_chat_file_id)
            greet_bot.build_new_img(last_chat_id, last_chat_caption)

        new_offset = last_update_id + 1


# запуск бота
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        exit()
