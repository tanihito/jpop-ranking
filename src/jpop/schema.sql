drop table if exists songs;
create table songs (
  utamap_id string primary key,
  title string not null,
  lyric string not null,
  artist string not null,
  youtube string not null,
  crawl_date date
);

drop table if exists ranking;
create table ranking (
  crawl_date date,
  rank integer,
  utamap_id string,
  primary key(crawl_date, rank)
);