## 与 Bing Chat 对话

## 前置要求

- 拥有可提前访问 https://bing.com/chat 的微软账户
- 机器人运行端可正常访问 Bing 国际版

## 安装

```
.plugin install Bing-AI
```

## 使用

### 获取 Cookie

- 安装 [Chrome](https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) 或 [Firefox](https://addons.mozilla.org/en-US/firefox/addon/cookie-editor/) 的 cookie 编辑器扩展
- 转到 `bing.com`
- 打开刚刚安装的扩展程序
- 单击右下角的“`导出`”（这会将您的 cookie 保存到剪贴板）
- 将您的 cookie 粘贴到 `<madoka>/app/data/extension_data/bing_gpt/cookies.json`

接下来重启 Madoka

## 鸣谢

- [Edge GPT](https://github.com/acheong08/EdgeGPT): The reverse engineering the chat feature of the new version of Bing
