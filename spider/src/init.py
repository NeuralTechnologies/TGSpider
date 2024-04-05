import asyncio
from telethon import TelegramClient, events
import os 
import app_logger
from telethon.errors.rpcerrorlist import SessionPasswordNeededError
from database import DBManager, config
loop = asyncio.get_event_loop()
logger = app_logger.get_logger(__name__)
db_manager = DBManager()
db_manager.initialize()

async def  main():
    db_session = db_manager.Session()
    tg_accounts = db_session.query(db_manager.Base.classes.tg_accounts).all()
    for tg_account in tg_accounts:
        tg_client = TelegramClient(str(os.getenv('DATA_DIRECTORY')) + '/' + tg_account.session_name, tg_account.api_id, 
                                   tg_account.api_hash)
        await tg_client.connect()
        if not await tg_client.is_user_authorized():
            print(tg_account.phone)
            await tg_client.send_code_request(tg_account.phone)
            try:
                await tg_client.sign_in(tg_account.phone, input('Enter the code: '))
            except SessionPasswordNeededError as err:
                await tg_client.sign_in(password=tg_account.password)
        tg_account.is_initialized = True
        db_session.commit()

    db_session.close()

loop.run_until_complete(main())
