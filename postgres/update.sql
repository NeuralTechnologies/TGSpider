ALTER TABLE public.telegram_sources
ADD COLUMN description VARCHAR DEFAULT NULL,
ADD COLUMN date_description TIMESTAMP WITHOUT TIME ZONE DEFAULT NULL;