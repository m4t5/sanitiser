drop table if exists story_index;
create table story_index(
  index_id integer primary key autoincrement,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  url text not null,
  title text,
  trail text
);

drop table if exists stories;
create table stories(
  story_id integer primary key autoincrement,
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  url text not null,
  story_text text not null
);