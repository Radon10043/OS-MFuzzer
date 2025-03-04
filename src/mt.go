// Description: Insert MR implementation into C source code and build the program
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
	"time"

	"github.com/seehuhn/mt19937"
)

// 全局变量
var (
	rng = rand.New(mt19937.New()) // 随机数生成器
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

// 将插入MR后的C代码编译为可执行文件
//
// Parameters:
//
//	srcSlice: 插入MR后的C代码内容
//	binPath: 可执行文件路径
//	compiler: 编译器
func buildProgram(srcSlice []byte, binPath string, compiler string) {
	// 写入修改后的C代码
	cPath := binPath + ".c"
	err := os.WriteFile(cPath, srcSlice, 0666)
	if err != nil {
		panic(err)
	}

	// 延迟删除插入MR后的源文件
	defer func() {
		if err := recover(); err != nil {
			fmt.Println(err)
		}
		os.Remove(cPath)
	}()

	// 编译新的C代码为可执行文件
	_, err = exec.Command(compiler, "-static", "-o", binPath, cPath).Output()
	if err != nil {
		panic(err)
	}
}

func runQemu() error {
	debug := false
	qemuBin := "qemu-system-x86_64"
	kernelObj := "/home/radon/Documents/kernel-fuzzing/linux-v6.2"
	kernelBin := filepath.Join(kernelObj, "arch", "x86", "boot", "bzImage")
	imageFile := "/home/radon/Documents/kernel-fuzzing/Debian/bullseye.img"
	// vmlinuxBin := filepath.Join(kernelObj, "vmlinux")
	sshKey := "/home/radon/Documents/kernel-fuzzing/Debian/bullseye.id_rsa"
	port := 10021
	qemuArgs := []string{"-m", "2048", "-smp", "2", "-chardev", "socket,id=SOCKSYZ,server=on,wait=off,host=localhost,port=13952", "-mon", "chardev=SOCKSYZ,mode=control", "-display", "none", "-serial", "stdio", "-no-reboot", "-name", "VM-0", "-device", "virtio-rng-pci", "-enable-kvm", "-cpu", "host,migratable=off", "-device", "e1000,netdev=net0", "-netdev", "user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:" + fmt.Sprint(port) + "-:22", "-hda", imageFile, "-snapshot", "-kernel", kernelBin, "-append", "root=/dev/sda console=ttyS0"}

	// 启动QEMU
	fmt.Printf("QEMU start command: %s %s\n", qemuBin, strings.Join(qemuArgs, " "))
	cmd := exec.Command(qemuBin, qemuArgs...)
	if debug {
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
	}
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start QEMU: %v", err)
	}

	// 将qemu进程ID写入文件
	qemuPid := cmd.Process.Pid
	pidFile := filepath.Join("/home/radon/Documents/projects/kernel-driver-MR-identify/qemu.pid")
	if err := os.WriteFile(pidFile, []byte(fmt.Sprint(qemuPid)), 0666); err != nil {
		return fmt.Errorf("failed to write QEMU PID to file: %v", err)
	}
	fmt.Printf("QEMU PID: %d\n", qemuPid)

	// 尝试运行ssh与QEMU通信
	time.Sleep(5 * time.Second) // 等待5秒
	sshArgs := []string{
		"-p", fmt.Sprint(port),
		"-F", "/dev/null",
		"-o", "UserKnownHostsFile=/dev/null",
		"-o", "IdentitiesOnly=yes",
		"-o", "BatchMode=yes",
		"-o", "StrictHostKeyChecking=no",
		"-o", "ConnectTimeout=10",
		"-i", sshKey,
		"-v",
		"root@localhost",
		"pwd",
	}
	fmt.Printf("SSH command: ssh %s\n", strings.Join(sshArgs, " "))
	cmd = exec.Command("ssh", sshArgs...)
	if debug {
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
	}
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to communicate with QEMU via ssh: %v", err)
	}
	fmt.Printf("Successfully connected to QEMU via ssh on port %d\n", port)

	// 将syzkaller的hello文件拷贝到QEMU中, 测试用
	scpArgs := []string{
		"-P", "10021",
		"-F", "/dev/null",
		"-o", "UserKnownHostsFile=/dev/null",
		"-o", "IdentitiesOnly=yes",
		"-o", "BatchMode=yes",
		"-o", "StrictHostKeyChecking=no",
		"-o", "ConnectTimeout=10",
		"-i", sshKey,
		"/home/radon/Documents/projects/kernel-driver-MR-identify/bin/hello",
		"root@localhost:/hello",
	}
	cmd = exec.Command("scp", scpArgs...)
	if debug {
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
	}
	fmt.Printf("Run SCP command: scp %s\n", strings.Join(scpArgs, " "))
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to copy file to qemu: %v", err)
	}

	// 运行一下hello, 获取其输出
	sshArgs = []string{
		"-p", fmt.Sprint(port),
		"-F", "/dev/null",
		"-o", "UserKnownHostsFile=/dev/null",
		"-o", "IdentitiesOnly=yes",
		"-o", "BatchMode=yes",
		"-o", "StrictHostKeyChecking=no",
		"-o", "ConnectTimeout=10",
		"-i", sshKey,
		"-v",
		"root@localhost",
		"/hello",
	}
	cmd = exec.Command("ssh", sshArgs...)
	tmp := cmd.Stdout
	fmt.Printf("Run SSH command: ssh %s\n", strings.Join(sshArgs, " "))
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to run hello via ssh: %v", err)
	}
	fmt.Printf("Output of hello: %s\n", tmp)

	return nil
}

func main() {
	// 命令行参数相关变量
	var (
		flagMR       = flag.String("mr", "", "MR Implementation file (.h)")
		flagCSrc     = flag.String("csrc", "", "C source file (.c)")
		flagCDir     = flag.String("cdir", "", "C source file directory (Conflicts with -csrc)")
		flagOut      = flag.String("out", "", "Directory that stores binaries.")
		flagCompiler = flag.String("compiler", "gcc", "Compiler to use")
	)

	// 解析命令行参数
	flag.Usage = func() {
		fmt.Println("Description: Insert MR implementation into C source code")
		fmt.Println("Usage: test [options]")
		flag.PrintDefaults()
	}
	flag.Parse()

	// 检查命令行参数, 若不符合要求则退出程序
	if *flagMR == "" || (*flagCSrc == "" && *flagCDir == "") || *flagOut == "" {
		flag.Usage()
		os.Exit(1)
	}

	// 检查-csrc和-cdir参数是否同时存在
	if *flagCSrc != "" && *flagCDir != "" {
		fmt.Println("Error: -csrc and -cdir cannot be used together")
		flag.Usage()
		os.Exit(1)
	}

	// 若out目录不存在则递归创建
	if _, err := os.Stat(*flagOut); os.IsNotExist(err) {
		os.MkdirAll(*flagOut, 0755)
	}

	err := runQemu()
	if err != nil {
		panic(err)
	}

	// 获取C源代码文件路径, 加入srcPaths切片中
	srcPaths := make([]string, 0)
	if *flagCSrc != "" {
		srcPaths = append(srcPaths, *flagCSrc)
	} else {
		// 获取目录下所有.c文件
		files, err := os.ReadDir(*flagCDir)
		if err != nil {
			panic(err)
		}
		for _, file := range files {
			if strings.HasSuffix(file.Name(), ".c") {
				srcPaths = append(srcPaths, filepath.Join(*flagCDir, file.Name()))
			}
		}
	}

	// 遍历所有C源代码文件, 为每个文件插入MR实现并编译为可执行文件
	for i, srcPath := range srcPaths {
		// 获取main函数中系统调用行号切片
		lSlice := getSyscallLinenos(srcPath)
		lSlice = lSlice[3:] // 使用syz-prog2c后前3个系统调用固定是syscall(__NR_mmap, ...), 去掉前三个系统调用

		// 将MR实现插入syzkaller生成的C代码中
		nsrcSlice := insertMRImpl(srcPath, *flagMR, lSlice)

		// 将修改后的C文件编译为可执行文件
		bn := filepath.Base(srcPath)
		bn = strings.TrimSuffix(bn, ".c") + "-mr"
		binPath := filepath.Join(*flagOut, bn)
		compiler := *flagCompiler
		buildProgram(nsrcSlice, binPath, compiler)
		fmt.Printf("\rBuild successfully: [%d/%d]", i+1, len(srcPaths))
	}
	fmt.Println("\n\nAll done!")
}
