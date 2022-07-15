create table if not exists Plugin_Sspanel_Account(
    qid char(10) not null comment 'QQ号',
    web varchar(50) not null comment '签到地址',
    user varchar(50) not null comment '登陆邮箱',
    pwd varchar(50) not null comment '登陆密码',
    primary key(qid, web, user)
);