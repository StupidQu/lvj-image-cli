# 图片上传工具

一个带工作量证明机制的命令行图片上传工具。

## 功能

- 从命令行接收 API 端点和多个图片路径参数
- 实现工作量证明机制，防止 API 滥用
- 使用多线程加速计算工作量证明
- 支持批量上传多张图片
- 上传图片并返回 URL
- 将所有上传链接集中显示在输出的最后

## 安装依赖

```bash
pip install requests
```

## 使用方法

```bash
python upload_image.py <API端点> <图片路径1> [图片路径2 图片路径3 ...]
```

示例:

```bash
# 上传单张图片
python upload_image.py http://example.com ./my_image.jpg

# 上传多张图片
python upload_image.py http://example.com ./image1.jpg ./image2.png ./image3.gif
```

## 工作流程

1. 对每个图片，从 API 获取工作量证明挑战
2. 计算符合条件的后缀
3. 上传图片和工作量证明
4. 收集所有成功上传的图片 URL
5. 在所有处理完成后，先输出上传统计信息
6. 最后集中输出所有上传链接

## 输出格式

程序会先输出处理过程的调试信息（英文），最后 N 行为 N 个上传成功的图片链接，便于用户直接复制。例如：

```
Processing file: ./image1.jpg
Challenge received: Difficulty N=6 bits, IP=192.168.1.1
Starting proof of work calculation (difficulty N = 6 bits)...
Thread 0 has tried 10000 times...
Thread 2 has tried 10000 times...
Valid suffix found!
Uploading image: ./image1.jpg...
Uploading...
Upload successful: ./image1.jpg

Processing file: ./image2.png
...

Upload complete: 2/2 files successfully uploaded

上传链接:
http://example.com/uploads/abc123.jpg
http://example.com/uploads/def456.png
```

## 工作量证明机制

服务器生成一个长为 64 字节的随机数`pref`作为前缀，程序需要找到一个长度为 64 字节的随机数`suff`作为后缀，使得`pref+suff`的 SHA-256 哈希值的前 N 位(bit)为 0。

N 的值由服务器根据用户请求频率动态调整，范围通常在 4 到 12 位之间。随着用户请求频率的增加，服务器会增加 N 的值，从而增加找到有效后缀的计算难度。

## 代码结构

代码使用面向对象的方式组织，主要包含以下组件：

- `ImageUploader` 类：处理工作量证明和图片上传的核心逻辑
- `main` 函数：解析命令行参数并协调上传流程
