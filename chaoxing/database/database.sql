create table if not exists chaoxing_sign (
    qid char(12) not null comment 'QQ',
    username char(11) not null comment '手机号',
    password varchar(256) not null comment '密码',
    latitude varchar(256) null default '-2' comment '纬度',
    longitude varchar(256) null default '-1' comment '经度',
    clientip varchar(20) not null comment 'IP地址',
    address varchar(256) null default '中国' comment '地址名',
    expiration_time datetime null comment '到期时间',
    auto_sign int null default 0 comment '自动签到状态',
    primary key (qid)
);