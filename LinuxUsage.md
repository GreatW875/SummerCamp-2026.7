# 一、shell基本命令

## 导航
`cd` + `/`进入根目录、`~`进入主目录、`..`返回上一级

`ls`查看当前目录下的文件 + `-l`同时查看权限、`-a`查看所有（包括隐藏文件）

`pwd`	查看当前目录路径
`tree`	查看当前目录结构

## 文件
`cp`	复制文件
`mv`	移动文件
`rm`	删除文件
`rmdir`	删除空目录
`rm -r/-rf`	删除目录下所有文件（询问/不询问）
`mkdir` 创建目录
`touch`	创建文件

`cat`	查看文件
`head`  查看文件前几行
`less (-N)`  分页查看文件（显示行号）
`tail`  查看文件后几行

## 查找
`find`  查找文件

`which` 在PATH中寻找可执行文件

`locate`    模糊查找

## 文本处理
`grep`

`sed`

`awk`

## 其他
`unzip [filename] -d [filepath]`	解压.zip文件到某路径

`sudo -i`	ubuntu用户进入root模式

`apt update`	更新软件包列表

`apt upgrade`	升级所有软件包

`apt autoremove`	删除无用的依赖包

`apt autoremove --purge`	彻底删除无用依赖及配置

`apt autoclean`	清理过时的软件包缓存

`apt clean`	清空所有软件包缓存

`apt purge <软件包名>`  彻底卸载软件及配置文件

### 自定义命令别名
`nano ~/.bashrc`	编辑bashrc配置文件

`alias [别名]='[命令]'`	添加自定义别名

`source ~/.bashrc`	使配置立即生效

---

# 二、conda操作
`conda --version`	查看conda版本号

`conda create --name [envname]`	创建环境

`conda env list`	查看现有环境

`conda activate [envname]`	激活环境

`conda deactivate`	使环境失活

`conda env remove --name [envname]`	删除环境

`conda/pip list`	列出包

`conda/pip install [packagename](== x.x)`	安装包

`conda update [packagename]`	更新包

`pip install --upgrade [packagename]`

`conda remove [packagename]`	删除包

`pip uninstall [packagename]`

`conda env export > environment.yml`  导出环境：

`conda env create -f environment.yml` 复现环境：

---

# 三、docker操作
`systemctl status docker`	查看docker运行状态

`systemctl start docker`    启动docker

`systemctl stop docker	`	停止docker（docker.service）

`systemctl stop docker.socket`	停止docker.socket（用于接收docker命令，会自动唤醒docker.service）

`docker pull (--platform=XXX) [镜像名]`	从仓库拉取（某某架构的）镜像
> **eg.** docker pull docker.io/library/nginx:latest -> docker pull nginx
> docker.io 仓库地址（这里是官方仓库，可省略）
> library 命名空间（这里是官方仓库的命名空间，可省略）
> nginx:latest 镜像标签名+版本名

`docker images`	列出镜像，镜像-->生成容器

`docker ps (-a)`	查看正在运行的（所有的）容器

`docker rmi [imagename]`	删除镜像

`docker rm (-f) [containername]`	（强制）删除容器

`docker run -it`

`docker start -ai [containername]`

`exit`

`docker volume create [挂载卷名]`

---

# 四、git操作
`git init`	创建版本仓库

`git status`	查看工作区、暂存区改动情况

`git log (--pretty=oneline) (--graph)`	查看版本记录

`git reflog`	查看操作记录

## 工作区内
`git rm [filename]`	删除文件

`git checkout -- [filename]`	丢弃工作区的改动

`git add [filename]`	将工作区（即git管理的目录）里需要提交的文件添加到暂存区

## 暂存区内
`git reset HEAD [filename]`	取消暂存区的改动

`git commit -m 'XXX'`	将暂存区里的内容提交到当前分支
> `feat:`新增
> `fix:`修bug
> `docs:`更新README
> `refactor:`代码重构
> `chore:`杂活

## 版本管理
`git reset --hard HEAD^ or HAED~1 or [版本号]`

`git diff HEAD[^……] (HEAD[^……]) -- [filename]`	对比不同版本中的这个文件

## 分支管理
`git branch`	查看分支及状态

`git branch [branchname]`	创建分支

`git branch -d [branchname]`	删除分支

`git checkout [branchname]`	切换分支

`git checkout -b [branchname]`	创建并切换分支

`git merge [branchname]` 合并分支到当前分支

`git merge --no-ff -m [branchname]` 不使用fast-forward模式合并分支（即创建新分支）

`git stash`	保存工作现场（包括工作区和暂存区），出现bug时使用

`git stash list`	列出被保存的工作现场

`git stash pop`	返回到工作现场
