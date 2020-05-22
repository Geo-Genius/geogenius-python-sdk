[TOC]
# 1 前提
需要基于python3的Anaconda3环境。内网下，conda和pip需要先配置代理。
# 2 部署sdk环境
## 2.1 安装基础python环境
生成基础conda python3.7环境，注意python版本必须是3.7
```
conda create -n {python_env_name} python=3.7 --yes
conda activate {python_env_name}
```
如果激活的时候报错，按照调试执行conda init，并重开shell console。
## 2.2 安装python依赖
进入项目根目录（注意conda下载rasterio会偶先报错，重试即可。
```
conda install --yes -c conda-forge --file requirements_conda.txt
pip install -r requirements.txt
```
由于内网代理不稳定会导致以下两种情况：
* 如果conda装rasterio的时候报错:**"Sloving environment: failed with current repodata"**，则重试
* 如果报错**SSL**或者**WinError**，则先配置代理，配置后若还有问题则重试：
```
# windows
set http_proxy=http://username:password@proxy.huawei.com:8080
set https_proxy=http://username:password@proxy.huawei.com:8080
# linux
export http_proxy='http://username:password@proxy.huawei.com:8080'
export https_proxy='http://username:password@proxy.huawei.com:8080'
```

* 如果设置代理后pip仍然报错**WinError**，则推荐用conda来安装pip安装失败的包，之后再用pip安装全部的包。
```
conda install --yes -c conda-forge package_name
pip install -r requirements.txt --proxy=http_proxy=http://username:password@proxy.huawei.com:8080
```

## 2.3 安装mapboxgl
将代码目录的mapboxgl/下的mapboxgl和mapboxgl-0.10.2-py3.7.egg-info两个文件夹拷贝到python环境下的Lib/site-package目录下。

测试如下
```
python -c 'from mapboxgl.viz import RasterTilesViz'
```
* 如果报错：**No module named chroma**或者**except Exception, e 是python3.7不允许的语法**，则
```
pip uninstall chroma-py --yes
pip install chroma-py
```
## 2.4 安装sdk到本地python
```
python setup.py build install
```
* 如果报错：**error: [WinError 5] 拒绝访问 mercantile.exe**，则执行
```
python setup.py build install --user
```
* 如果内网下install中下载包很慢，可以先退出，用pip或者conda安装对应的包，然后继续install
* 如果报错**SSL**或者**WinError**，则先配置代理，配置后若还有问题则重试：
```
# windows
set http_proxy=http://username:password@proxy.huawei.com:8080
set https_proxy=http://username:password@proxy.huawei.com:8080
# linux
export http_proxy='http://username:password@proxy.huawei.com:8080'
export https_proxy='http://username:password@proxy.huawei.com:8080'
```

# 3 分发mapbobgl和sdk到外部python
用下面工具生成二进制编译包，在dist目录下找到编译包分发给外部python，解压到外部python的Lib/site-package目录下即可使用
```
python setup.py bdist
```
测试如下
```
python -c 'from geogeniustools import CatalogImage'
```