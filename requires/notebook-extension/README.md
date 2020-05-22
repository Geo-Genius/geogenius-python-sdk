geogenius jupyter notebook extensions
=======================

notebook插件，可以实现页面和服务拓展。

Installation
------------
1. 项目打包  
`python setup.py install`

2. 如已安装notebook，安装插件  
`jupyter nbextension install --py geogenius_jupyter_notebook_extensions --sys-prefix`
  
`jupyter nbextension enable geogenius_jupyter_notebook_extensions --py --sys-prefix`

3. 设置插件参数（iframe目标地址）  
`set_config "http://100.94.14.213:8080/extensions/notebook"`


Change logs
-------
[0.1.0] 初始版本，实现了数据搜索面板插件