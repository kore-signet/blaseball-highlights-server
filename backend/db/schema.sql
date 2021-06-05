create table users (
  username text,
  user_id text PRIMARY KEY,
  user_token text,
  UNIQUE (user_id,user_token)
);

create table stories (
  story_id text PRIMARY KEY,
  game_id uuid,
  user_id text REFERENCES users (user_id),
  title text
);

create table events (
  story_id text REFERENCES stories (story_id),
  blaseball_event_id uuid,
  description text,
  visual jsonb,
  UNIQUE(story_id,blaseball_event_id)
);
