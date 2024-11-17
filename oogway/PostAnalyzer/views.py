from dotenv import dotenv_values
from telethon.sync import TelegramClient, events
from telethon.tl.types import PeerChannel
from Channels.TestChannel import TestChannel


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
                    PeerChannel(int(config["CHANNEL_TEST"])),
                ]
            ),
        )
        # client.add_event_handler(
        #     handle_message_edit,
        #     events.MessageEdited(
        #         chats=[
        #             PeerChannel(int(config["CHANNEL_TEST"])),

        
        #         ]
        #     ),
        # )
        await client.run_until_disconnected()
    # await client.disconnect()
    # return JsonResponse({"posts": []})


async def channelTest(msg):
    p1 = TestChannel()
    await p1.extractDataFromMessage(msg)
    




options = {
    int(config["CHANNEL_TEST"]): channelTest,


}
