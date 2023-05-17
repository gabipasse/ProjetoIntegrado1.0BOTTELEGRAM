import os

import telebot

BOT_TOKEN = os.environ.get('BOT_TOKEN')

bot = telebot.TeleBot(BOT_TOKEN)

import pymongo

from pymongo.server_api import ServerApi

from PIL import Image

from pillow_heif import register_heif_opener

conn = os.environ.get('MONGODB_CONN')

client = pymongo.MongoClient(conn, server_api=ServerApi('1'))

CarbonFree = client.CarbonFree


def get_exif(filename):
    image = Image.open(filename)

    if ".HEIC" in filename:

        image.save(filename.replace(".HEIC", ".jpg"), 'JPEG')

    else:

        image.save(filename.replace(".heic", ".JPG"), 'JPEG')

    image.verify()

    return image.getexif().get_ifd(0x8825)


def get_geotagging(exif):
    geo_tagging_info = {}

    if not exif:

        raise ValueError("No EXIF metadata found")
    else:

        gps_keys = ['GPSLatitudeRef', 'GPSLatitude', 'GPSLongitudeRef', 'GPSLongitude']

        i = 0

        for k, v in exif.items():

            if i == 4:
                break

            if type(v) == tuple:

                myList = []

                for i in range(len(v)):
                    myList.append(float(v[i]))

                v = myList

                geo_tagging_info[gps_keys[k - 1]] = v

                i += 1

        return geo_tagging_info


@bot.message_handler(commands=["comandos"])
def send_welcome(message):
    bot.reply_to(message,
                 "Digite /usuarios para acessar informacoes dos usuarios, /areas para acessar informacoes das areas ou envie uma imagem como documento heic para armazena-la!")


@bot.message_handler(commands=["usuarios"])  # filtros
def usuarios(message):

    bot.reply_to(message, "Enviando os dados")

    for usuarioDado in CarbonFree.UsuariosQR.find({}):  # separar a chave da imagem

        dadosRetornar = dict(usuarioDado)

        bot.reply_to(message, str(dadosRetornar))


@bot.message_handler(commands=["areas"])
def areas(message):

    bot.reply_to(message, "Enviando os dados:")

    for areaDado in CarbonFree.VistoriaDados.find({}):

        for key, value in areaDado["geoData"].items():
            bot.reply_to(message, str(value))

        image = areaDado["pathJPG"]

        with open(image, 'rb') as photo:

            bot.send_photo(chat_id=message.chat.id, photo=photo)


@bot.message_handler(content_types=['document'])
def handle_document(message):

    bot.reply_to(message, "Verificando imagem e dados!")

    file_info = bot.get_file(message.document.file_id)

    file_name = message.document.file_name

    if not file_name.lower().endswith(".heic"):
        bot.reply_to(message, "Envie apenas arquivos/imagens como documento heic.")

        return

    downloaded_file = bot.download_file(file_info.file_path)

    usuario = []

    for usuarioDado in CarbonFree.UsuariosQR.find({"_id": message.chat.id}):
        usuario.append(usuarioDado)

    if len(usuario) > 1:
        bot.reply_to(message, "Erro ao realizar operação.")

        raise ValueError("Dois usuarios com mesmo id presentes no banco de dados!")

    with open(message.document.file_name, "wb") as f:

        f.write(downloaded_file)

    register_heif_opener()

    my_image = message.document.file_name

    image_info = get_exif(my_image)

    results = get_geotagging(image_info)

    CarbonFree.VistoriaDados.insert_one({

        "geoData": results,

        "pathHeic": message.document.file_name,

        "pathJPG": message.document.file_name.lower().replace(".heic", ".jpg"),

        "autor": message.chat.id

    })

    bot.reply_to(message, "Foto inserida com sucesso!")

    if not usuario:
        CarbonFree.UsuariosQR.insert_one({

            "_id": message.chat.id,

            "visitas": 1,

            "visitados:": [],

            "usuarioTipo": "visitante",

        })

        bot.reply_to(message, "Seja bem vindo!")


if __name__ == "__main__":
    bot.infinity_polling()
