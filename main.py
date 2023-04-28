import sys
import requests as rq
import datetime as dt
import time as tm
import json
from pprint import pprint

RMT_FOLDER_PATH = 'some_folder_name'  # input('Remote folder name: ')
PHOTOS_COUNT = 5

VK_TOKEN = ''
VK_USER_ID = ''
VK_ALBUM_ID = ''

YAD_TOKEN = ''


def get_dttm_str():
    return f'{str(dt.datetime.now())[:-4]} - '


class VkUserPhotos:
    def __init__(self,
                 user_id=VK_USER_ID,
                 token=VK_TOKEN,
                 album_id=VK_ALBUM_ID
                 ):
        self.user_id = user_id
        self.token = token
        self.album_id = album_id

    def get_photos_lst(self):
        response = rq.get(url='https://api.vk.com/method/photos.get',
                          params={'user_id': self.user_id,
                                  'access_token': self.token,
                                  'album_id': self.album_id,
                                  'extended': '1',
                                  'v': '5.81'
                                  }
                          )
        if response.status_code >= 400:
            print('В get_photos_lst: '
                  f'произошла ошибка. Код: {response.status_code}')
            pprint(response.json())
            print('Sorry')
            return
        response_items = dict(response.json())['response']['items']

        result = []
        for item in response_items:
            for size_type, size, url in \
                    sorted([(size['type'],
                             size['height'] * size['width'],
                             size['url']
                             )
                            for size in item['sizes']
                            ], reverse=True
                           ):
                result.append({'id': item['id'],
                               'size_type': size_type,
                               'size': size,
                               'likes': item['likes']['count'],
                               'date': tm.strftime('%d%m%y',
                                                   tm.gmtime(item['date'])
                                                   ),
                               'url': url
                               })
                break
        return result

    def get_photo(self, url: str):
        response = rq.get(url=url,
                          params={'access_token': self.token}
                          )
        return response


class YaUploader:
    def __init__(self, token=YAD_TOKEN):
        self.token = token
        self.url = 'https://cloud-api.yandex.net/v1/disk/resources'

    def get_headers(self):
        return {'Content-Type': 'application/json',
                'Authorization': f'OAuth {self.token}'
                }

    def get_files_list(self):
        response = rq.get(url=self.url + '/files', headers=self.get_headers())
        return response.json()

    def make_folder(self, folder_path=RMT_FOLDER_PATH):
        response = rq.put(url=self.url,
                          headers=self.get_headers(),
                          params={'path': folder_path}
                          )
        if response.status_code == 201:
            print(f'{get_dttm_str()}YAD-folder \'{folder_path}\' '
                  'successfully created.')
        else:
            print(f'{get_dttm_str()}Code {response.status_code}.\n'
                  f'YAD.make_folder(\'{folder_path}\')')
            pprint(response.json())

    def drop_folder(self, folder_path: str):
        response = rq.delete(url=self.url,
                             headers=self.get_headers(),
                             params={'path': folder_path}
                             )
        if response.status_code == 204:
            print(f'{get_dttm_str()}YAD-folder \'{folder_path}\' '
                  'successfully deleted.')
        else:
            print(f'{get_dttm_str()}Code {response.status_code}.\n'
                  f'YAD.drop_folder(\'{folder_path}\')')
            pprint(response.json())

    def _get_upload_link(self, yad_file_path: str):
        response = rq.get(url=self.url + '/upload',
                          headers=self.get_headers(),
                          params={'path': yad_file_path, 'overwrite': 'true'}
                          )
        return response.json()

    def upload_file_to_disk(self, yad_file_path: str, bfile: bytes):
        href = self._get_upload_link(yad_file_path=yad_file_path).get('href',
                                                                      ''
                                                                      )
        response = rq.put(url=href, data=bfile)
        response.raise_for_status()
        if response.status_code == 201:
            print(f'{get_dttm_str()}YAD-file \'{yad_file_path}\' '
                  'uploaded successfully.')
        else:
            print(f'{get_dttm_str()}Code {response.status_code}.\n'
                  f'YAD.upload_file_to_disk(\'{yad_file_path}\', '
                  f'{type(bfile)})')
            pprint(response.json())


if __name__ == '__main__':
    print(f'{get_dttm_str()}Load started.'
          'Wait a few seconds, please.')
    sys.stdout = open('log.txt', 'w')
    print(f'{get_dttm_str()}Load started.')

    yad_uploader = YaUploader()
    yad_uploader.make_folder()

    user_photos = VkUserPhotos()
    file_names_lst = []
    load_report = []
    for idx, photo in enumerate(sorted(user_photos.get_photos_lst(),
                                       key=lambda x: x['size'],
                                       reverse=True
                                       )
                                ):
        if idx >= PHOTOS_COUNT:
            break

        if photo['likes'] not in file_names_lst:
            file_name = photo['likes']
        elif f"{photo['likes']}_{photo['date']}" not in file_names_lst:
            file_name = f"{photo['likes']}_{photo['date']}"
        else:
            file_name = f"{photo['likes']}_{photo['date']}_{idx - 1}"
        file_names_lst.append(file_name)

        photo_response = user_photos.get_photo(photo['url'])
        for ct in [photo_response.headers['Content-Type']]:
            file_name = f'{file_name}.{ct[ct.find("/") + 1:]}'
            file_path = f'{RMT_FOLDER_PATH}/{file_name}'

        yad_uploader.upload_file_to_disk(yad_file_path=file_path,
                                         bfile=photo_response.content
                                         )
        load_report.append({'file_name': file_name,
                            'size': photo['size_type']
                            })
    with open('load_report.json', 'wt') as f:
        f.write(json.dumps(load_report))
    print(f'{get_dttm_str()} Done.')
    sys.stdout = sys.__stdout__
    print('Load id over. Please, check the log.txt and load_report.json'
          ' files for more information./')
