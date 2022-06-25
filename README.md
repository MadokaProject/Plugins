# Plugins
Madoka 插件中心

## 使用方法

### 推荐

使用 Madoka 自带的插件管理器安装插件

### 手动

将所需插件目录复制到 `app/plugin/extension` 目录即可。

插件所需要的其他库写明在插件内的requirements.txt文件

## 贡献

您可以将您自己编写的插件提交至此插件库，在 `list.json` 文件中填写该插件的相关信息，同时你的插件目录中必须有 `resource.json` 文件记录除 `requirements.txt` 以外的所有文件。

为避免插件重复，请将插件目录命名为 `作者名_插件名`

### 示例

#### 插件结构

``` txt
.
└── example    # 插件目录名，建议为插件名
    ├── main.py
    ├── requirements.txt  # 依赖文件(pypi)
    ├── example1          # 资源文件1
    ├── example2          # 资源文件2
    ├── example3          # 资源文件3
    └── resource.json     # 资源清单

```

### 资源清单 (resource.json)

``` json
[
    "main.py",
    "example1",
    "example2",
    "example3"
]
```

### 插件信息 (list.json)

``` json
[
    ...,
    {
        "name": "示例插件",
        "root_dir": "example",
        "author": "example_author",
        "version": "0.0.1",
        "pypi": true,
        "description": "演示如何创建/贡献一个新的插件"
    },
    ...
]
```

> 如果你的插件需要安装其它依赖包，请在插件目录中放入 `requirement.txt` 文件并在插件信息中将 `pypi` 设为 `true`