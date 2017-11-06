import os
import re
import argparse

slash = '\\'


def parse_code(file_name):
    # 按二进制读取文件内容
    file_content = open(file_name, 'rb').read()
    # 转换成文本字符串
    file_content = repr(file_content)
    
    # 字符串可能是双引号包围（“***”）或单引号包围（‘***'）
    # 单引号包围的字符串中出现的单引号字符（’）要变为 "\'"，在正则表达式中为 "\\'"
    if file_content[1] == '"':
        singlequate = "'"
        re_singlequate = "'"
    else:
        singlequate = r"\'"
        re_singlequate = r"\\'"

    # 去除注释
    file_content = re.sub(r"/\*(.+?)\*/", "", file_content)
    # 去除mzphp2自动加上的 error_reporting(E_ALL^E_NOTICE);语句
    file_content = re.sub(r"error_reporting\(E_ALL\^E_NOTICE\);", "", file_content)
    # 去除所有的回车换行符
    file_content = re.sub(r"(?:\\n)|(?:\\r)", "", file_content)
    # 去除所有mzphp2加上的随机不可读字符串
    file_content = re.sub(r";(?:\\x[a-f0-9]{2})+;", ";", file_content)
    # 所有 !0 变为 true
    file_content = re.sub("!0", "true", file_content)
    # 所有 !1 变为 false
    file_content = re.sub("!1", "false", file_content)

    # mzphp2把代码中的所有函数名（最顶层函数除外），变量名，字符串与数值常量都收集到一个大的数组中
    # 然后用一串随机字符作为间隔，将这个大数组连接成一个很长的字符串

    # 寻找混淆用的长字符串，提取出需要的信息，然后去除

    global var_name
    global var_key
    global var_list

    def get_var_list(repl):
        global var_name
        global var_key
        global var_list
        # 记录用哪一个超全局变量保存的
        var_name = repl.group(1)
        # 记录超全局变量中保存var_list用的key
        var_key = repl.group(2).replace(slash, slash * 2)
        # 记录所有被替换的函数名，变量名和常量值
        var_list = repl.group(4).split(repl.group(3))
        return ''

    # 混淆前的字符串数组通常保存在GLOBALS，_SERVER或_GET这几个超全局变量中
    # 后面紧跟着一个explode函数调用
    file_content = re.sub(r"\$((?:GLOBALS)|(?:_SERVER)|(?:_GET))\[((?:\\x[a-f0-9]{2})+?)\] = explode\(\s*" + re_singlequate + r"(.+?)" + re_singlequate + r"\s*,\s*"+ re_singlequate + r"((?:[^'\\]|(?:\\')|(?:\\?))*)" + re_singlequate + r"\s*\);", get_var_list, file_content)
    
    # 去除mzphp2添加的 define(..., '...'); 语句
    file_content = re.sub(r"define\(\s*" + re_singlequate + var_key + re_singlequate + r"\s*,\s*" + re_singlequate + r"(?:\\x[a-f0-9]{2})+" + re_singlequate + r"\s*\);", "", file_content)

    # 把所有类似 {$GLOBALS{var_key}[hex_id]} 形式的语句替换为原来的变量名或函数名
    file_content = re.sub(
        r"{\$" + var_name + r"{" + var_key + r"}[\[\{]((?:0)|(?:0x[a-f0-9]+?))[\]\}]}",
        lambda x: var_list[int(x.group(1), 16)],
        file_content
    )

    # 把所有类似 $GLOBALS{var_key}[hex_id]( var... 形式的语句替换为原来的函数名+(
    file_content = re.sub(
        r"\$" + var_name + r"{" + var_key + r"}[\[\{]((?:0)|(?:0x[a-f0-9]+?))[\]\}]\(",
        lambda x: var_list[int(x.group(1), 16)] + "(",
        file_content
    )

    # 把所有类似 $GLOBALS{var_key}[hex_id] 形式的语句替换为原来的字符串，再加上首尾的单引号
    file_content = re.sub(
        r"\$" + var_name + r"{" + var_key + r"}[\[\{]((?:0)|(?:0x[a-f0-9]+?))[\]\}]",
        lambda x: singlequate + var_list[int(x.group(1), 16)] + singlequate,
        file_content
    )

    # 在每一个函数里mzphp2会用一个本地变量指向混淆用的 $GLOBALS{var_key}
    # 即 $xxx = $GLOBALS{var_key}; 的形式
    # 在函数内部混淆后的变量不是 $GLOBALS{var_key}[hex_id] 样式 而是 $xxx[hex_id] 样式
    # 需要提取所有的函数内部的 $xxx 变量， 再分别替换

    global mnc
    global var_list_instance

    mnc = 0
    var_list_instance = []

    def rp_var(repl):
        global var_list_instance
        if repl.group(1) not in var_list_instance:
            var_list_instance.append(repl.group(1))
        return ''

    # 记录各个函数内的混淆用变量到 var_list_instance数组中
    file_content = re.sub(r"(\$(?:\\x[a-f0-9]{2})+)=&\$" + var_name + r"{" + var_key + r"};", rp_var,
                          file_content)

    # 排序，不是必需的步骤，但是感觉会提高一些效率。纯感觉，无证据...
    var_list_instance.sort(key=lambda x: len(x), reverse=True)

    for instance in var_list_instance:
        # 同上面一样， 分 {$xxx[hex_id]}, $xxx[hex_id](, $xxx[hex_id] 三种情况分别替换
        file_content = re.sub(slash + repr(instance)[1:-1] + r"{[\[\{]((?:0)|(?:0x[a-f0-9]+?))[\]\}]}",
                              lambda x: var_list[int(x.group(1), 16)],
                              file_content)
        file_content = re.sub(slash + repr(instance)[1:-1] + r"[\[\{]((?:0)|(?:0x[a-f0-9]+?))[\]\}]\(",
                              lambda x: var_list[int(x.group(1), 16)] + "(",
                              file_content)
        file_content = re.sub(slash + repr(instance)[1:-1] + r"[\[\{]((?:0)|(?:0x[a-f0-9]+?))[\]\}]",
                              lambda x: singlequate + var_list[int(x.group(1), 16)] + singlequate,
                              file_content)

    mnc = 0
    var_list_instance = {}

    # 所有函数内部的局部变量名都被混淆成了不可读的字符
    # 下面就把这些变量名用 $var_1，$var_2...之类的名字来替换

    def fix_var(repl):
        global var_list_instance
        global mnc
        if repl.group(1) not in var_list_instance:
            var_list_instance[repl.group(1)] = "$_var_" + str(mnc)
            mnc += 1
        return var_list_instance[repl.group(1)]

    file_content = re.sub(r"(\$(?:\\x[a-f0-9]{2})+)", fix_var, file_content)

    # 把代码里的所有十六进制数转为十进制形式
    file_content = re.sub(r'(0x[0-9a-f]+)', lambda x: str(int(x.group(1), 16)), file_content)

    # 把字符串形式的文件恢复成二进制数据
    file_content = eval(file_content)

    return file_content

if __name__ == '__main__':
    # 添加命令行参数处理
    parser = argparse.ArgumentParser(description='mzphp2 deobfuscator tool')
    parser.add_argument('f', metavar="mzphp2 obfuscated file", help='mzphp2 obfuscated file')
    parser.add_argument('o', metavar="Output deobfuscated file", help='output deobfuscated file')
    args = parser.parse_args()
    if not os.path.isfile(args.f):
        raise FileNotFoundError
    result = parse_code(args.f)

    # 如果不指定输出文件，输出结果到控制台
    if args.o is not None:
        with open(args.o, 'wb') as of:
            of.write(result)
    else:
        print(result)