from dotenv import dotenv_values
from telethon.sync import TelegramClient, events
from telethon.tl.types import PeerChannel
from .classes.BinanceProMsg import BinanceProMsg
from .classes.RastadMsg import RastadMsg
from Channels.FeyzianChannel import FeyzianChannel
from Channels.AliBeyroChannel import AliBeyroChannel


config = dotenv_values(".env")

api_id = config["api_id"]
api_hash = config["api_hash"]

username = config["username"]


async def get_user_posts_view(request):
    async with TelegramClient(username, api_id, api_hash) as client:

        async def handle_new_message(event):
            # try:
            await options[event.message.peer_id.channel_id](event.message)

            # except:
            #     print("An exception occurred")

        # async def handle_message_edit(event):
            # try:
            #     msg = event.message
            # except:
            #     print("An exception occurred")

        client.add_event_handler(
            handle_new_message,
            events.NewMessage(
                chats=[
                    PeerChannel(int(config["CHANNEL_FEYZ"])),
                    PeerChannel(int(config["CHANNEL_TEST_FEYZIAN"])),

                    PeerChannel(int(config["CHANNEL_ALI_BEY"])),
                    PeerChannel(int(config["CHANNEL_TEST_ALI_BEYRANVAND"])),

                    PeerChannel(int(config["CHANNEL_BINANCE_PRO"])),
                    PeerChannel(int(config["CHANNEL_TEST_BINANCE_PRO"])),

                    PeerChannel(int(config["CHANNEL_RASTAD"])),
                    PeerChannel(int(config["CHANNEL_TEST_RASTAD"])),
                ]
            ),
        )
        # client.add_event_handler(
        #     handle_message_edit,
        #     events.MessageEdited(
        #         chats=[
        #             PeerChannel(int(config["CHANNEL_FEYZ"])),
        #             PeerChannel(int(config["CHANNEL_TEST_FEYZIAN"])),

        #             PeerChannel(int(config["CHANNEL_ALI_BEY"])),
        #             PeerChannel(int(config["CHANNEL_TEST_ALI_BEYRANVAND"])),
        
        #             PeerChannel(int(config["CHANNEL_BINANCE_PRO"])),
        #             PeerChannel(int(config["CHANNEL_TEST_BINANCE_PRO"])),
        #         ]
        #     ),
        # )
        await client.run_until_disconnected()
    # await client.disconnect()
    # return JsonResponse({"posts": []})


async def channelFeyzian(msg):
    p1 = FeyzianChannel()
    await p1.extractDataFromMessage(msg)
    
async def channelTestRastad(msg):
    p1 = RastadMsg()
    await p1.extract_data_from_message(msg)


async def channelAliBeyro(msg):
    p1 = AliBeyroChannel()
    await p1.extractDataFromMessage(msg)

async def channelTestBinancePro(msg):
    # print(msg)
    p1 = BinanceProMsg()
    await p1.extract_data_from_message(msg)


options = {
    int(config["CHANNEL_FEYZ"]): channelFeyzian,
    int(config["CHANNEL_TEST_FEYZIAN"]): channelFeyzian,

    int(config["CHANNEL_ALI_BEY"]): channelAliBeyro,
    int(config["CHANNEL_TEST_ALI_BEYRANVAND"]): channelAliBeyro,

    int(config["CHANNEL_BINANCE_PRO"]): channelTestBinancePro,
    int(config["CHANNEL_TEST_BINANCE_PRO"]): channelTestBinancePro,

    int(config["CHANNEL_RASTAD"]): channelTestRastad,
    int(config["CHANNEL_TEST_RASTAD"]): channelTestRastad,

}
