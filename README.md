1. Необходимо выполнить docker compose up -d postgres
2. Если у Вас уже была ранее поднята БД TGspider то необходимо перед пунктом  1  выполнить  docker compose down -v postgres  -- это команда удалит все старые файлы
3. После создания БД - проверить что таблички создались, согласно схеме, что в tg_accounts - есть 4 записи, а в potential_telegram_sources 1481 запись. Схема БД - https://dbdiagram.io/d/660f4be903593b6b613ac26
4. Запустить docker compose run -i spider-init
5. Система запросит коды, которые можно получить у меня, предварительно согласов время, когда Вы будите переносить систему.
6. Можно скопировать файлы сессии - из папки spider-data - тогда коды запрашивать не будет, однако меня все равно надо предупредить так как - я должен акцептовать ваш IP в телеграмме.
7. Предварительно Вы можете изменить данные в конфиге - по пожеланиям Алексея - что какой-параметр означает я описал  вот тут: https://docs.google.com/document/d/1y5xGi_XNA9PX4SY7TaY5IKUz-YMT3jA_CVLtSCK-C3E/edit?usp=sharing
8. Запустить паука командой docker compose up -d spider
9. После этого должны пойти логи в тг группе - которая указана в конфиге (можете поменять если хотите)
10. Посмотреть логи можно docker compose logs -f spider
11. Я много сегодня тестировал на этих аккаунтах - поэтому пожалуйста не ставьте больше 50 значение tg_limit - сколько каналов может опработать один аккаунт в эти сутки, я много уже потратил - с завтрашнего дня можно ставить 150.
