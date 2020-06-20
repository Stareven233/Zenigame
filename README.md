## Zenigame 
团队工作协调管理应用  
支持用户登录注册，团队考勤打卡，问卷发布，文件上传，即时通讯...

[Api文档](https://www.showdoc.cc/708582510680717)


## 环境
Virtualenv(Python3.7)  


## 安装
在合适目录下执行：
>$ git clone git@github.com:Stareven233/Zenigame.git  
>$ cd chatti

### 依赖：
>$ virtualenv -p /usr/bin/python3 venv  
>$ source venv/bin/activate  
>$ pip3 install -r requirements.txt  


### 数据库：
- 安装MySQL  
- python manage.py db migrate  
- python manage.py db upgrade  


## 启动  
>$ python Zenigame.py  
