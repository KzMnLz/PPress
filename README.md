<div align="center">
    <img src="app/static/favicon.ico" width="90px" alt="PPress">
</div>

<h1 align="center" style="margin: 2px 0 30px; font-weight: bold;">
    PPress
</h1>

<h4 align="center">一个基于Python的博客CMS系统，采用Flask极致构建</h4>

## 简介
PPress 是一个基于 Flask 框架构建的功能丰富的博客CMS系统，具备内存缓存、缓存预热等优化机制，支持 sqlite 和 mysql 两种数据库。

拥有完善的前后台管理系统，涵盖用户管理、文章管理、评论管理、系统配置管理等多个方面，是一个适合任何Web的开源 Blog / CMS 平台。

## 功能

文章模块
- 文章管理
- 文章分类
- 文章标签
- 文章发布
- 文章搜索
- 文章浏览

分类模块
- 分类管理

页面模块
- 页面管理
- 页面评论

用户相关
- 用户管理
- 权限管理
- 用户标签
- 历史浏览管理
- 可视化浏览信息

系统相关
- 模版管理
- 插件管理
- 系统管理
- 网站管理
- 附件管理

## 特点

模版模块
- 模版在线配置、管理

插件模块
- 插件在线安装、卸载
- 插件在线启用、停止
- 插件在线更新
- 支持插件的导入、导出

用户模块
- 独立的登录和注册页面
- 验证码判断登录注册放行
- 记录用户浏览历史
- 管理用户个人信息

角色和权限
- 角色管理
- 角色升降级分配

其他
- Python文本情感分析TextBlog分析文章情感
- 可选sqlite代替MySQL免数据库环境安装

## 截图
![A.png](preview/A.png)

![B.png](preview/B.png)

## 运行
Centos7下PPress启动教程：https://www.bilibili.com/video/BV1jezSY3Eag/

Windows下PPress启动教程：https://www.bilibili.com/video/BV1sEzSYHEHc/

### 文字教程
1. 下载代码，解压缩
2. 安装依赖 pip install -r requirements.txt
3. 运行 run.py - 进入网页安装 - 填写对应的配置信息 - 安装成功后重启本应用
4. 后台地址：`/admin/`  默认管理员账号（admin/123456）

## 文档

doc：http://doc.gank.fun/web/#/627038158/

## 许可证

本项目采用 MIT 许可证,详情请参阅 [LICENSE](LICENSE) 文件。