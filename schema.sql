drop table if exists story_index;
create table story_index(
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  id integer primary key autoincrement,
  url text not null,
  title text,
  trail text
);

drop table if exists stories;
create table stories(
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  id integer primary key autoincrement,
  url text not null,
  title text,
  story text not null,
  comments text
);

drop table if exists letter_index;
create table letter_index(
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  id integer primary key autoincrement,
  url text not null,
  title text,
  trail text
);

drop table if exists letters;
create table letters(
  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  id integer primary key autoincrement,
  url text not null,
  title text,
  letter text not null,
  comments text
);
