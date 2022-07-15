create table if not exists Plugin_NetEase_Account(
    qid char(12) not null comment 'QQ号',
    phone char(11) not null comment '登录手机',
    pwd char(20) not null comment '登录密码'
);