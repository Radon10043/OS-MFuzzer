package main

import (
	"flag"
	"fmt"
	"math/rand/v2"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/seehuhn/mt19937"
)

// 命令行参数相关变量
var (
	flagMR       = flag.String("mr", "", "MR Implementation file (.h)")
	flagCSrc     = flag.String("csrc", "", "C source file (.c)")
	flagOut      = flag.String("out", "", "Output file (Binary file)")
	flagCompiler = flag.String("compiler", "gcc", "Compiler to use")
)

var (
	rng = rand.New(mt19937.New())
)

// 获取C代码main函数中的系统调用最后的位置
// 返回行号切片, 目的是为了后续插入MR实现
//
// Parameters:
//
//	csrcPath: C源代码文件路径
//
// Returns:
//
//	返回C代码main函数中系统调用行号切片
func getSyscallLinenos(csrcPath string) []int {
	// 获取系统调用的py文件绝对路径
	repoDir := filepath.Dir(filepath.Dir(os.Args[0]))
	pyFilePath := filepath.Join(repoDir, "src", "CAnalysis.py")

	// 调用py文件获取C代码main函数中的系统调用
	pythonBin := filepath.Join(repoDir, ".venv", "bin", "python3")
	out, err := exec.Command(pythonBin, pyFilePath, "--file", csrcPath).Output()
	if err != nil {
		panic(err)
	}

	// 将输出结果按行根据逗号进行切割
	lines := strings.Split(string(out), "\n")
	lines = lines[:len(lines)-1] // 去掉最后一个空行
	lSlice := make([]int, 0)
	for _, line := range lines {
		lst := strings.Split(line, ",")
		lineno, err := strconv.Atoi(lst[1])
		if err != nil {
			panic(err)
		}
		lSlice = append(lSlice, lineno)
	}
	return lSlice
}

// 将MR实现插入syzkaller生成的C代码中
//
// Parameters:
//
//	csrcPath: C源代码文件路径
//	mrPath: MR实现文件路径
//	lSlice: C源码main函数中系统调用行号切片
//
// Returns:
//
//	返回插入MR实现后的C代码内容, 以字节切片形式返回
func insertMRImpl(csrcPath string, mrPath string, lSlice []int) []byte {
	// 读取C代码内容
	csrc, err := os.ReadFile(csrcPath)
	if err != nil {
		panic(err)
	}

	// 找到最后#include的行
	csrcSlice := strings.Split(string(csrc), "\n")
	lastIncludeLine := 0
	for i, line := range csrcSlice {
		if strings.HasPrefix(line, "#include") {
			lastIncludeLine = i
		} else if strings.HasPrefix(line, "#define") || strings.HasPrefix(line, "//") || line == "" {
			continue
		} else {
			break
		}
	}

	// 将[#include "/path/to/mr.h"]插入到最后#include的行之后
	mrInclude := fmt.Sprintf("\n#include \"%s\"", mrPath)
	csrcSlice[lastIncludeLine] += mrInclude
	randIndex := rng.IntN(len(lSlice))
	csrcSlice[lSlice[randIndex]-1] += "\n\tMR();"

	// 将插入MR实现后的C代码内容按字节切片返回
	return []byte(strings.Join(csrcSlice, "\n"))
}

func buildProgram(srcSlice []byte, binPath string, compiler string) {
	// 写入修改后的C代码
	cPath := binPath + ".c"
	err := os.WriteFile(cPath, srcSlice, 0666)
	if err != nil {
		panic(err)
	}

	// 编译新的C代码为可执行文件
	_, err = exec.Command(compiler, "-static", "-o", binPath, cPath).Output()
	if err != nil {
		panic(err)
	}

	// 删除文件
	err = os.Remove(cPath)
	if err != nil {
		panic(err)
	}
}

func main() {
	// 解析命令行参数
	flag.Usage = func() {
		fmt.Println("Description: Insert MR implementation into C source code")
		fmt.Println("Usage: test [options]")
		flag.PrintDefaults()
	}
	flag.Parse()

	// 检查命令行参数, 若不符合要求则退出程序
	if *flagMR == "" || *flagCSrc == "" || *flagOut == "" {
		flag.Usage()
		os.Exit(1)
	}

	// 获取main函数中系统调用行号切片
	lSlice := getSyscallLinenos(*flagCSrc)
	lSlice = lSlice[3:] // syz-prog2c前3个系统调用固定是syscall(__NR_mmap, ...), 去掉前三个系统调用

	// 将MR实现插入syzkaller生成的C代码中
	nsrcSlice := insertMRImpl(*flagCSrc, *flagMR, lSlice)

	// 将修改后的C文件编译为可执行文件
	binPath := *flagOut
	compiler := *flagCompiler
	buildProgram(nsrcSlice, binPath, compiler)
	fmt.Println("Build program successfully")
	fmt.Println("Binary Path:", binPath)
}
