import asyncio
from datetime import datetime
from telethon import TelegramClient, functions
import datetime
import re
from telethon.tl.types import Channel, ChannelParticipantsAdmins
import app_logger
import requests
from database import DBManager, config
from telethon.errors.rpcerrorlist import SessionPasswordNeededError
import os
import pytz
from multiprocess.pool import ThreadPool

utc = pytz.UTC
db_manager = DBManager()
db_manager.initialize()
logger = app_logger.get_logger(__name__)


async def get_messages(tg_client, entity, telegram_source, db_session, thread_id):
    try:
        min_id = 0
        count = 0
        async for m in tg_client.iter_messages(entity, min_id=min_id, limit=None):
            if (m.date > utc.localize(
                    datetime.datetime.strptime(config['SETTINGS']['messages_date_start'], '%Y-%m-%d'))
                    and count < config['SETTINGS']['messages_limit']):
                msg = db_manager.Base.classes.messages()
                msg.telegram_sources_id = telegram_source.id
                msg.date = m.date
                msg.message = m.message
                msg.sender_id = m.sender_id
                msg.message_id = m.id
                msg.processing = False
                db_session.add(msg)
                count = count + 1
                if count % 1000 == 0:
                    logger.info(f'Thread {thread_id}: Processing {entity.title}  Download {count} messages')
            else:
                break
        db_session.commit()
    except Exception as e:
        logger.info(e)


async def get_admins(tg_client, db_session, link, ts_id):
    # Many channels hide admins - so an error may appear here
    try:
        async for user in tg_client.iter_participants(link, filter=ChannelParticipantsAdmins):
            if not user.bot:
                # Add an admin to the list of admins
                ta = db_manager.Base.classes.telegram_admins()
                ta.telegram_id = user.id
                ta.nic = user.username
                if db_session.query(db_manager.Base.classes.telegram_admins).filter(
                        db_manager.Base.classes.telegram_admins.telegram_id == ta.telegram_id).first() is None:
                    db_session.add(ta)
                    db_session.commit()
                    db_session.flush()
                    # Adding a connection between the admin and the channel
                    sa = db_manager.Base.classes.sources_admins()
                    sa.sources_id = ts_id
                    sa.admins_id = ta.id
                    db_session.add(sa)
                    db_session.commit()
                else:
                    # print('This admin is already in the database.')
                    # Adding a channel connection with an existing admin
                    sa = db_manager.Base.classes.sources_admins()
                    sa.sources_id = ts_id
                    sa.admins_id = db_session.query(db_manager.Base.classes.telegram_admins).filter(
                        db_manager.Base.classes.telegram_admins.telegram_id == ta.telegram_id).first().id
                    db_session.add(sa)
                    db_session.commit()
    except Exception as e:
        logger.info(e)


def add_to_telegram_tree(db_session, parent_id, child_id, date_formation_edge):
    tt = db_manager.Base.classes.telegram_tree()
    tt.parent_id = parent_id
    tt.child_id = child_id
    tt.date_formation_edge = date_formation_edge
    tt.date_create_row = datetime.datetime.now()
    db_session.add(tt)
    db_session.commit()


def check_tg(link):
    r = requests.get(link)
    if 'View in Telegram' in r.text:
        return True
    else:
        return False


class link_item:
    def __init__(self, nic, date):
        self.nic = nic
        self.date = date


def post_processing(ts_id, db_session, thread_id):
    logger.info(f"Thread {thread_id}: We process messages tg channel with id = {ts_id} in search of new links")
    ms = db_session.query(db_manager.Base.classes.messages).filter(
        db_manager.Base.classes.messages.processing == False).filter(
        db_manager.Base.classes.messages.telegram_sources_id == ts_id).all()
    ms_total_count = len(ms)
    logger.info(f"Thread {thread_id}: Total number of messages in the source: {ms_total_count}")
    links = []
    _links = []
    for m in ms:
        if m.message is not None:
            # Mark the message as processed
            db_session.query(db_manager.Base.classes.messages).filter(
                db_manager.Base.classes.messages.id == m.id).first().processing = True
            _nics = re.findall(r'@[a-zA-Z0-9_]{5,}|https://t.me\S+', m.message)
            for _nic in _nics:
                if '@' in _nic:
                    _nic = 'https://t.me/' + _nic.replace('@', '')
                    if _nic.lower() not in _links:
                        _link = link_item(_nic.lower(), m.date)
                        links.append(_link)
                        _links.append(_nic.lower())
    links_count = len(links)
    logger.info(f"Thread {thread_id}:  Total number of potential links: {links_count}")
    potential_links = []
    for link in links:
        if check_tg(link.nic):
            logger.info(f'Thread {thread_id}: Good Link {str(link.nic).replace('https://t.me/', '')}')
            potential_links.append(link.nic)
            pts = db_manager.Base.classes.potential_telegram_sources()
            pts.link = link.nic
            pts.parent_id = ts_id
            pts.date_formation_edge = link.date
            pts.date_create_row = datetime.datetime.now()
            db_session.add(pts)
    check_links_count = len(potential_links)
    db_session.query(db_manager.Base.classes.telegram_sources).filter(
        db_manager.Base.classes.telegram_sources.id == ts_id).first().childs_count = check_links_count
    db_session.commit()
    logger.info(f"Thread {thread_id}:  Total number of good links: {check_links_count}")


async def processing_telegram_source(link, parent_id, date_formation_edge, db_session, tg_client, thread_id, i):
    # Check if there is a source with this link
    telegram_source = db_session.query(db_manager.Base.classes.telegram_sources).filter(
        db_manager.Base.classes.telegram_sources.link == link).first()
    if telegram_source is not None:
        logger.info(f'Thread {thread_id} )channel №{(i- thread_id * config['SETTINGS']['tg_limit'])} '
                    f'processing username:  {str(link).replace('https://t.me/','')}'
                    f' is already in the list of sources')
        add_to_telegram_tree(db_session, parent_id, telegram_source.id, date_formation_edge)
    else:
        # It often happens that the telegram account no longer exists
        try:
            entity = await tg_client.get_entity(link)
            # if entity.username is not None:
            username = entity.username
            logger.info(f'Thread {thread_id} channel №{(i- thread_id * config['SETTINGS']['tg_limit'])}  '
                        f'processing username:  {username}')
            # If the entity is a channel or group, then we take all messages and write them to the database
            # If entity is just a user then we do nothing
            if isinstance(entity, Channel):
                telegram_source = db_manager.Base.classes.telegram_sources()
                telegram_source.link = link
                telegram_source.username = username
                if entity.megagroup:
                    telegram_source.is_group = True
                    telegram_source.is_channel = False
                else:
                    telegram_source.is_group = False
                    telegram_source.is_channel = True
                telegram_source.telegram_id = entity.id
                telegram_source.caption = entity.title
                full_data = await tg_client(functions.channels.GetFullChannelRequest(entity))
                telegram_source.participants_count = full_data.full_chat.participants_count
                # If this source is already in the database, then we do nothing
                ts_in_db = (db_session.query(db_manager.Base.classes.telegram_sources).filter
                            (db_manager.Base.classes.telegram_sources.username ==
                             telegram_source.username).first())
                if ts_in_db is None:
                    telegram_source.date_processing = datetime.datetime.now()
                    db_session.add(telegram_source)
                    db_session.commit()
                    db_session.flush()
                    # Many channels hide admins - so an error may appear here
                    await get_admins(tg_client, db_session, link, telegram_source.id)
                    # Adding all messages from the channel to the database
                    await get_messages(tg_client, entity, telegram_source, db_session, thread_id)
                    add_to_telegram_tree(db_session, parent_id, telegram_source.id, date_formation_edge)
                    post_processing(telegram_source.id, db_session, thread_id)
                else:
                    logger.info('This channel is already in the database.')
                    add_to_telegram_tree(db_session, parent_id, ts_in_db.id, date_formation_edge)

            else:
                logger.info('This account is not a group, not a channel.')
        except Exception as e:
            logger.info(e)


async def thread_spider(k, potential_telegram_sources):
    db_session = db_manager.Session()
    tg_accounts = db_session.query(db_manager.Base.classes.tg_accounts).all()
    tg_account = tg_accounts[k]
    tg_client = TelegramClient(str(os.getenv('DATA_DIRECTORY')) + '/' + tg_account.session_name, tg_account.api_id,
                               tg_account.api_hash)
    await tg_client.connect()
    if not await tg_client.is_user_authorized():
        await tg_client.send_code_request(tg_account.phone)
        try:
            await tg_client.sign_in(tg_account.phone, input('Enter the code: '))
        except SessionPasswordNeededError as err:
            await tg_client.sign_in(password=tg_account.password)
    i = k * config['SETTINGS']['tg_limit']
    while i < (k + 1) * config['SETTINGS']['tg_limit']:
        await processing_telegram_source(potential_telegram_sources[i].link, potential_telegram_sources[i].parent_id,
                                         potential_telegram_sources[i].date_formation_edge,
                                         db_session, tg_client, k, i)
        db_session.query(db_manager.Base.classes.potential_telegram_sources).filter(
            db_manager.Base.classes.potential_telegram_sources.id ==
            potential_telegram_sources[i].id).first().is_processing = True
        db_session.commit()
        i = i + 1
    db_session.close()


def main():
    logger.info('Start TGSSpider...')

    # Determine the date and time a day ago to determine the accounts that can be used
    day_ago = (datetime.datetime.now() - datetime.timedelta(days=1)).astimezone(pytz.utc)
    print(day_ago)
    db_session = db_manager.Session()

    # Select accounts that are initialized and that have not been used for more than a day
    tg_accounts = (db_session.query(db_manager.Base.classes.tg_accounts).filter(
        db_manager.Base.classes.tg_accounts.is_initialized == True).filter(db_manager.Base.classes.tg_accounts.date_end_used < day_ago).all())

    logger.info(f'Number of accounts ready to use: {len(tg_accounts)}')

    # Check that the number of threads is less than the number of accounts
    if config['SETTINGS']['threads'] > len(tg_accounts):
        threads_count = len(tg_accounts)
    else:
        threads_count = config['SETTINGS']['threads']

    logger.info(f'Number of threads use: {threads_count}')

    if len(tg_accounts) > 1:
        # Set the start date and time of using the account
        for tg_account in tg_accounts:
            tg_account.date_start_used = datetime.datetime.now().astimezone(pytz.utc)
        db_session.commit()

        potential_telegram_sources = db_session.query(db_manager.Base.classes.potential_telegram_sources).filter(
            db_manager.Base.classes.potential_telegram_sources.is_processing == False).all()

        logger.info(f'Number of potential tg accounts:: {len(potential_telegram_sources)}')

        required_threads_count = int(len(potential_telegram_sources) / config['SETTINGS']['tg_limit']) + 1

        if required_threads_count < threads_count:
            threads_count = required_threads_count

        cors = [thread_spider(i, potential_telegram_sources) for i in range(threads_count)]

        with ThreadPool(threads_count) as executor:
            executor.map(asyncio.run, cors)

        # Set the end date and time of using the account
        for tg_account in tg_accounts:
            tg_account.date_end_used = datetime.datetime.now().astimezone(pytz.utc)
        db_session.commit()

    else:
        logger.info(f'no active accounts!')
    db_session.close()


if __name__ == '__main__':
    main()

