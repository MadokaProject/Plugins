create table if not exists word_dict(
    word varchar(50) not null,
    pos varchar(50) not null,
    tran varchar(200) not null,
    bookId varchar(50) not null
);