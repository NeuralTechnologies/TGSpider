import datetime
import re
import app_logger
from database import DBManager, config
import os
import pytz
from openai import OpenAI
import tiktoken
import time

utc = pytz.UTC
db_manager = DBManager()
db_manager.initialize()
logger = app_logger.get_logger(__name__)

client = OpenAI(
    api_key=config['SETTINGS']['openai_key'],
)


def num_tokens_from_messages(messages, model="gpt-3.5-turbo"):
    """Return the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        print("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    if model in {
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k-0613",
        "gpt-4-0314",
        "gpt-4-32k-0314",
        "gpt-4-0613",
        "gpt-4-32k-0613",
    }:
        tokens_per_message = 3
        tokens_per_name = 1
    elif model == "gpt-3.5-turbo-0301":
        tokens_per_message = 4  # every message follows <|start|>{role/name}\n{content}<|end|>\n
        tokens_per_name = -1  # if there's a name, the role is omitted
    elif "gpt-3.5-turbo" in model:
        print("Warning: gpt-3.5-turbo may update over time. Returning num tokens assuming gpt-3.5-turbo-0613.")
        return num_tokens_from_messages(messages, model="gpt-3.5-turbo-0613")
    elif "gpt-4" in model:
        print("Warning: gpt-4 may update over time. Returning num tokens assuming gpt-4-0613.")
        return num_tokens_from_messages(messages, model="gpt-4-0613")
    else:
        raise NotImplementedError(
            f"""num_tokens_from_messages() is not implemented for model {model}. See https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to tokens."""
        )
    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def clean_text(text):
    # Removes all characters except letters, numbers, punctuation, and special characters
    cleaned_text = re.sub(r'[^\w\s,.!?;:()"\'&%$@#*-]', '', text)
    # Removing extra whitespace and empty lines
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
    return cleaned_text

def main():
    db_session = db_manager.Session()

    telegram_source = db_session.query(db_manager.Base.classes.telegram_sources).filter(db_manager.Base.classes.telegram_sources.description ==  None).filter(db_manager.Base.classes.telegram_sources.childs_count !=  None).all()
    for ts in telegram_source:
        try:
            all_messages = ''
            ai_messages = [
            {"role": "system", "content": "Make a brief description of the channel telegrams based on these messages"},
            {"role": "user", "content": all_messages}
                ]

            messages = db_session.query(db_manager.Base.classes.messages).filter(
                db_manager.Base.classes.messages.telegram_sources_id == ts.id).filter(
                db_manager.Base.classes.messages.message != None).filter(
                db_manager.Base.classes.messages.message != '').order_by(
                db_manager.Base.classes.messages.date.desc()).all()
            if len(messages) > 0:
                for m in messages:
                    if num_tokens_from_messages(ai_messages) < config['SETTINGS']['tokens']:
                        all_messages += clean_text(m.message)
                        ai_messages = [
                                    {"role": "system",
                                     "content": "Make a brief description of the channel telegrams based on these messages"},
                                    {"role": "user", "content": all_messages}
                                    ]
                    else:
                        break
                completion = client.chat.completions.create(
                                    model="gpt-3.5-turbo",
                                    #max_tokens=20,
                                    messages= ai_messages)
                logger.info(ts.link)
                logger.info(completion.choices[0].message.content)
                ts.description = completion.choices[0].message.content
            else:
                logger.info(ts.link)
                logger.info('There are not enough messages to build a description')
                ts.description = 'There are not enough messages to build a description'

        except Exception as e:
            logger.info(ts.link)
            ts.description = 'error'
            logger.info(e)
        finally:
            ts.date_description  = utc.localize(datetime.datetime.now())
            db_session.commit()


    db_session.close()




if __name__ == '__main__':
    main()
