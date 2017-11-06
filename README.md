mzphp2-deobfuscator
======
最近在学习某源码时遇到几个文件是经过混淆的。新学PHP，没有遇到过PHP的代码混淆，因此开动搜索引擎稍微研究了一下。

通过检测工具发现是采用mzphp2混淆的，在[这个地方](http://enphp.djunny.com/ "http://enphp.djunny.com/") 提供了在线的源码混淆服务，感谢作者的辛勤工作和无私奉献。

## 混淆原理
上传了几段PHP代码进行混淆，对比一下混淆前后的代码，大致可以推测出混淆的思路：
1. 收集代码中所有的函数名、变量名、字符和数值常量，整理成一个Array，这里我就叫它var_list；
2. 生成一小段随机字符str_separater，通过implode函数把var_list里的所有项连接成为一个很长的字符串str_obfus，各项之间使用str_separater连接；
3. 把var_list保存在GLOBAL、_SERVER或_GET之类的超全局变量中，所用的key（我命名为var_key）为一串不可读随机字符，于是

        $GLOBALS{var_key} = var_list = explode(str_separater, str_obfus);
    代码中原先可读的函数名，变量名，常量数值都被转化成了$GLOBALS{var_key}[hex_id]的形式；

4. 在每一个函数实现代码中，采用一个局部变量$xxx指向$GLOBAL{var_key}，局部变量$xxx的变量名通常也是一串不可读随机字符；
这样，在函数实现代码中，函数名，变量名，常量数值等被转化成了$xxx[hex_id]的形式。然后，函数实现代码段中的所有其它局部变量名都被转化成随机不可读字符串；
5. 还有，代码中所有的true转化为!0，所有的false转化为!1；
6. 此外，代码中随机添加一些不可读随机字符组成的最后以”;“结尾的行，PHP在执行到这行时只会报告“未定义过的常量”错误，不影响原有代码逻辑的执行。在代码最前面添加error_reporting(E_ALL^E_NOTICE); 防止报错停止PHP的执行；
7. 再是，代码头部添加define(var_key, '随机字符串')，估计是防止后面的$GLOBAL{var_key}报出变量未定义的错误；
8. 最后，去除所有的换行符。加上mzphp2的注释（可选）。

最终，原来的可读代码变成一堆天书。

## 解混淆方法
基本上就是上述原理的逆过程。
1. 去除所有注释，换行符。
2. 找到类似$GLOBALS{var_key} = explode(str_separater, str_obfus);这一句，提取出超全局变量的名字var_name，所用的key：var_key，以及所有被替换的名字数组：var_list；
3. 依照索引hex_id，把代码中的所有$GLOBALS{var_key}[hex_id]的形式的文本替换为var_list[hex_id]的值；
4. 在每个函数实现中寻找$xxx=$GLOBALS{var_key};这一句，保存变量名$xxx到var_list_instance数组中，把函数中所有$xxx[hex_id]形式的文本替换为原来的值；
5. 查找每段函数实现代码中的局部变量，这些变量的名字被替换成了不可读字符串。把它们找出来，依次用$var_1，$var_2...替换；
6. 最后，做一些格式整理，去除掉一些不需要的语句，还有替换回true和false等。

## 使用方法
程序用python语言实现，主要通过正则表达式的匹配和替换实现。运行需要python3，因为python2中str和unicode的不同使得代码中不可读字符的处理很麻烦，而python3中统一了str，从根本上支持unicode，不需要区分编码。

执行命令

    python3 mzphp_deobfuscator.py mzphp_obfuscated.php
输出结果到控制台，或

    python3 mzphp_deobfuscator.py mzphp_obfuscated.php mzphp_deobfuscated.php
输出结果到文件 mzphp_deobfuscated.php 。

## 几个注意的地方
1. 输出的文件没有格式美化，代码里没有换行，全都堆在一起。推荐使用[php-cs-fixer](https://github.com/FriendsOfPHP/PHP-CS-Fixer "https://github.com/FriendsOfPHP/PHP-CS-Fixer")美化一下；
2. 代码中的局部变量名被混淆了无法恢复，只能替换为$var_1，$var_2...格式；

    （我有个大胆的猜想，有没有可能mzphp2的作者把原始的局部变量名收集起来，经过处理/混淆/打散成不可读的字符串，这些字符串实际上包含了可以用来恢复变量名的信息。而混淆后代码中插入的不可读随机字符组成的最后以”;“结尾的行实际上就是这些字符串。目前以我的水平无法求证，有没有大神可以解答一下。）
2. 不支持经过gz字符串压缩的mzphp混淆。其实实现起来不难，寻找gzinflate(substr(gz_bytes, 0xa, -8));这一句，取出gz_bytes，在python中decompress就行了。只不过懒癌发作，没什么挑战性的工作提不起劲来，谁有兴趣帮忙实现一下;
3. 输入的php代码必须是utf-8编码的，其他格式的编码不能保证程序能正常工作（没有测试过非utf-8编码的文件，但是应该没有谁会用非utf-8的编码格式写PHP了吧）；
4. 程序只是通过正则表达式的匹配和替换来实现，不排除在某些特殊的情况下不能恢复原有代码逻辑，甚至可能破坏原始代码逻辑的情况；
5. 程序只是**能工作**，缺乏错误和异常处理，只是一个概念的实现，不能在生产环境中应用。
6. 在发布前，发现了[这个项目](https://github.com/FunnyStudio/mzphp2_decrypt "https://github.com/FunnyStudio/mzphp2_decrypt") 和本项目的目的基本一致，方法也差不多。他的程序结构比我的面条式代码要合理一些，于是借用了他的程序结构和变量命名，把我的程序重构了一下。感谢FunnyStudio的卓越工作。

最后，强调一下，这个程序只是一项技术研究和实现，请不要用来破解或修改他人程序。破解、修改他人版权的软件，这属于违法行为。对于这种行为，希望大家一起抵制。