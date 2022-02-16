# Plugins
Madoka 插件中心

## 使用方法

### 推荐

使用 Madoka 自带的插件管理器安装插件

### 手动

将所需插件目录内所有文件复制到 `app/plugin/extension` 目录即可。

插件所需要的其他库写明在插件内的requirements.txt文件

## 贡献

您可以将您自己编写的插件提交至此插件库，文件夹名需与插件执行文件名一致，并在 `list.json` 文件中填写该插件的相关信息。

> 示例：插件执行文件名: demo.py，目录名则为: demo
> ``` json
> {
>   "demo": {
>     "name": "插件中文名",
>     "author": "插件作者",
>     "version": "插件版本(用于判断更新)",
>     "resource": [
>         "demo.jpg",
>         "demoDir/",
>     ], # 资源文件直接写文件名, 目录用'/'结尾
>     "pypi": true / false  # 是否需要安装其他库，请将requirements.txt文件直接放入该目录
>   }
> }
> ```
> 该json会下载demo目录下的 `demo.py`、`demo.jpg`、`demoDir/*`，并保存为：
> ```
> app/plugin/extension/demo/: demo.py demo/
> ../demo/demo/: demo.jpg demoDir/