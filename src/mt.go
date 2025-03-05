// Description: Insert MR implementation into C source code and build the program
package main

import (
	"bytes"
	"context"
	"flag"
	"fmt"
	"math/rand/v2"
	"os"
	"os/exec"
	"path/filepath"
	"slices"
	"strconv"
	"strings"
	"time"

	"github.com/seehuhn/mt19937"
)

type Qemu struct {
	bin  string   // qemu-system-x86_64
	args []string // qemu启动参数
	pid  int      // qemu进程ID
	pidf string   // qemu进程ID文件路径
	inst exec.Cmd // qemu进程实例
}

type SSH struct {
	bin  string   // ssh
	args []string // ssh启动参数
}

type SCP struct {
	bin  string   // scp
	args []string // scp启动参数
}

type VM struct {
	qemu *Qemu
	ssh  *SSH
	scp  *SCP
}

// 命令行参数相关变量
var (
	flagMR       = flag.String("mr", "", "MR Implementation file (.h)")
	flagCSrc     = flag.String("csrc", "", "C source file (.c)")
	flagCDir     = flag.String("cdir", "", "C source file directory (Conflicts with -csrc)")
	flagOut      = flag.String("out", "", "Directory that stores binaries.")
	flagCompiler = flag.String("compiler", "gcc", "Compiler to use")
)

// 全局变量
var (
	rng = rand.New(mt19937.New()) // 随机数生成器
)

// 启动qemu
func (qemu *Qemu) boot() error {
	cmd := exec.Command(qemu.bin, qemu.args...)
	if err := cmd.Start(); err != nil {
		return fmt.Errorf("failed to start QEMU: %v", err)
	}

	// 将qemu进程ID写入文件
	qemu.pid = cmd.Process.Pid
	qemu.pidf = filepath.Join(*flagOut, "qemu.pid")
	qemu.inst = *cmd
	if err := os.WriteFile(qemu.pidf, []byte(fmt.Sprint(qemu.pid)), 0666); err != nil {
		return fmt.Errorf("failed to write QEMU PID to file: %v", err)
	}
	return nil
}

// 停止Qemu
func (qemu *Qemu) stop() error {
	// 杀死QEMU进程
	err := qemu.inst.Process.Kill()
	if err != nil {
		return fmt.Errorf("failed to stop QEMU: %v", err)
	}

	// 等待资源释放
	qemu.inst.Wait()
	return nil
}

// 重启Qemu
func (qemu *Qemu) restart() error {
	fmt.Printf("Restarting QEMU...\n")

	// 停止Qemu
	if err := qemu.stop(); err != nil {
		return fmt.Errorf("failed to restart QEMU: %v", err)
	}

	// 启动Qemu
	if err := qemu.boot(); err != nil {
		return fmt.Errorf("failed to restart QEMU: %v", err)
	}

	return nil
}

// 运行SSH命令, 返回标准输出, 标准错误和错误
func (ssh *SSH) run(command string) (bytes.Buffer, bytes.Buffer, error) {
	var stdout, stderr bytes.Buffer
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// 设置SSH命令参数并运行
	sshArgs := append(ssh.args, command)
	cmd := exec.CommandContext(ctx, ssh.bin, sshArgs...)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()

	// 命令运行超时
	if ctx.Err() == context.DeadlineExceeded {
		// Timeout, it's ok
	} else if err != nil {
		return stdout, stderr, fmt.Errorf("failed to run SSH command: %v", err)
	}

	return stdout, stderr, nil
}

// 运行SCP命令, 将src路径文件拷贝到dst路径
func (scp *SCP) run(src string, dst string) error {
	var stdout, stderr bytes.Buffer
	scpArgs := append(scp.args, src, dst)
	cmd := exec.Command(scp.bin, scpArgs...)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to run SCP command: %v", err)
	}
	return nil
}

// 创建VM实例, 包含Qemu, SSH, SCP
func create() (*VM, error) {
	qemu := &Qemu{
		bin: "qemu-system-x86_64",
		args: []string{
			"-m", "2048",
			"-smp", "2",
			"-chardev", "socket,id=SOCKSYZ,server=on,wait=off,host=localhost,port=13952",
			"-mon", "chardev=SOCKSYZ,mode=control",
			"-display", "none",
			"-serial", "stdio",
			"-no-reboot",
			"-name", "VM-0",
			"-device", "virtio-rng-pci",
			"-enable-kvm",
			"-cpu", "host,migratable=off",
			"-device", "e1000,netdev=net0",
			"-netdev", "user,id=net0,restrict=on,hostfwd=tcp:127.0.0.1:10021-:22",
			"-hda", "/home/radon/Documents/kernel-fuzzing/Debian/bullseye.img",
			"-snapshot",
			"-kernel", "/home/radon/Documents/kernel-fuzzing/linux-v6.2/arch/x86/boot/bzImage",
			"-append", "root=/dev/sda console=ttyS0",
		},
	}

	ssh := &SSH{
		bin: "ssh",
		args: []string{
			"-p", "10021",
			"-F", "/dev/null",
			"-o", "UserKnownHostsFile=/dev/null",
			"-o", "IdentitiesOnly=yes",
			"-o", "BatchMode=yes",
			"-o", "StrictHostKeyChecking=no",
			"-o", "ConnectTimeout=10",
			"-i", "/home/radon/Documents/kernel-fuzzing/Debian/bullseye.id_rsa",
			"-v",
			"root@localhost",
		},
	}

	scp := &SCP{
		bin: "scp",
		args: []string{
			"-P", "10021",
			"-F", "/dev/null",
			"-o", "UserKnownHostsFile=/dev/null",
			"-o", "IdentitiesOnly=yes",
			"-o", "BatchMode=yes",
			"-o", "StrictHostKeyChecking=no",
			"-o", "ConnectTimeout=10",
			"-i", "/home/radon/Documents/kernel-fuzzing/Debian/bullseye.id_rsa",
		},
	}

	vm := &VM{
		qemu: qemu,
		ssh:  ssh,
		scp:  scp,
	}

	return vm, nil
}

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
	bn := filepath.Base(binPath)
	cPath := filepath.Join(*flagOut, "csrc", bn+".c")
	err := os.WriteFile(cPath, srcSlice, 0666)
	if err != nil {
		panic(err)
	}

	// 编译新的C代码为可执行文件
	_, err = exec.Command(compiler, "-static", "-o", binPath, cPath).Output()
	if err != nil {
		panic(err)
	}
}

// 获取目录下所有.c文件, 返回文件路径切片
func getSrcPaths(cDir string) []string {
	files, err := os.ReadDir(cDir)
	if err != nil {
		panic(err)
	}
	srcPaths := make([]string, 0)
	for _, file := range files {
		if strings.HasSuffix(file.Name(), ".c") {
			srcPaths = append(srcPaths, filepath.Join(cDir, file.Name()))
		}
	}
	return srcPaths
}

// 将MR实现插入syzkaller生成的C代码中并进行编译, 返回可执行文件路径切片
func buildMRPrograms(srcPaths []string, mrPath string, outDir string, compiler string) []string {
	binPaths := make([]string, 0)
	for i, srcPath := range srcPaths {
		fmt.Printf("\r[%4d/%-4d] %-30s", i+1, len(srcPaths), "Build "+filepath.Base(srcPath)+" with MR")

		// 获取main函数中系统调用行号切片
		lSlice := getSyscallLinenos(srcPath)
		lSlice = lSlice[3:] // 使用syz-prog2c后前3个系统调用固定是syscall(__NR_mmap, ...), 去掉前三个系统调用

		// 将MR实现插入syzkaller生成的C代码中
		nsrcSlice := insertMRImpl(srcPath, mrPath, lSlice)

		// 将修改后的C文件编译为可执行文件
		bn := filepath.Base(srcPath)
		bn = strings.TrimSuffix(bn, ".c") + "-mr"
		binPath := filepath.Join(outDir, bn)
		buildProgram(nsrcSlice, binPath, compiler)
		binPaths = append(binPaths, binPath)
	}
	fmt.Printf("\n")
	return binPaths
}

func runProgram(vm *VM, binPath string) error {
	// 拷贝可执行文件到qemu中
	err := vm.scp.run(binPath, "localhost:/"+filepath.Base(binPath))
	if err != nil {
		return err
	}

	// 运行可执行文件
	command := fmt.Sprintf("/kcovtrace /%s 2>&1", filepath.Base(binPath))
	stdout, _, err := vm.ssh.run(command)
	if err != nil {
		return err
	}

	// 将PC写入文件
	pcPath := filepath.Join(*flagOut, "pc", filepath.Base(binPath)+"-pc")
	err = os.WriteFile(pcPath, stdout.Bytes(), 0666)
	if err != nil {
		return fmt.Errorf("failed to write PC to file\n%v", err)
	}

	// 删除可执行文件
	_, _, err = vm.ssh.run("rm /" + filepath.Base(binPath))
	if err != nil {
		return fmt.Errorf("failed to delete %s in vm\n%v", filepath.Base(binPath), err)
	}

	return nil
}

// 在vm中运行所有可执行文件
func runPrograms(binPaths []string) error {
	// 创建VM实例
	fmt.Printf("Creating VM...\n")
	vm, err := create()
	if err != nil {
		return err
	}

	// 启动qemu
	fmt.Printf("Booting VM...\n")
	err = vm.qemu.boot()
	if err != nil {
		return err
	}

	// 函数终止时关闭qemu
	defer vm.qemu.stop()

	// 与qemu进行交互, 查看能否连接成功
	time.Sleep(5 * time.Second)
	fmt.Printf("Handshaking with VM...\n")
	_, _, err = vm.ssh.run("pwd")
	if err != nil {
		return err
	}

	// 将kcovtrace拷贝到qemu中
	fmt.Printf("Copy kcovtrace to VM...\n")
	mtBin, _ := os.Executable()
	kcovtraceBin := filepath.Join(filepath.Dir(mtBin), "kcovtrace")
	err = vm.scp.run(kcovtraceBin, "localhost:/kcovtrace")
	if err != nil {
		return err
	}

	// 在qemu中运行所有可执行文件
	for i, binPath := range binPaths {
		fmt.Printf("\r[%4d/%-4d] %-30s", i+1, len(binPaths), "Executing "+filepath.Base(binPath))

		// 尝试运行可执行文件3次
		progPass := false
		for j := 0; j < 3; j++ {
			err = runProgram(vm, binPath)
			if err == nil {
				progPass = true
				break
			}
		}

		// 成功了, 继续下一个测试用例; 失败了, 重启qemu后再尝试3次
		if progPass {
			continue
		}
		vm.qemu.restart()
		time.Sleep(5 * time.Second)
		if _, _, err := vm.ssh.run("pwd"); err != nil {
			return fmt.Errorf("failed to handshake with VM after restart: %v", err)
		}

		for j := 0; j < 3; j++ {
			err = runProgram(vm, binPath)
			if err == nil {
				progPass = true
				break
			}
		}

		// 仍然失败, 跳过这个测试用例, 打印信息
		if !progPass {
			fmt.Printf("\nShit, Failed to run %s\n", filepath.Base(binPath))
		}
	}
	fmt.Printf("\nDone.\n")

	return nil
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

	// 删除原先的out目录, 创建新的out目录
	if _, err := os.Stat(*flagOut); err == nil {
		os.RemoveAll(*flagOut)
	}
	os.Mkdir(*flagOut, 0777)
	os.Mkdir(filepath.Join(*flagOut, "csrc"), 0777)
	os.Mkdir(filepath.Join(*flagOut, "binaries"), 0777)
	os.Mkdir(filepath.Join(*flagOut, "pc"), 0777)

	// 获取C源代码文件路径, 加入srcPaths切片中
	srcPaths := make([]string, 0)
	if *flagCSrc != "" {
		srcPaths = append(srcPaths, *flagCSrc)
	} else {
		srcPaths = getSrcPaths(*flagCDir)
	}
	slices.SortFunc(srcPaths, func(a, b string) int {
		if len(a) == len(b) {
			return strings.Compare(a, b)
		}
		return len(a) - len(b)
	})

	// 遍历所有C源代码文件, 为每个文件插入MR实现并编译为可执行文件
	binOutPath := filepath.Join(*flagOut, "binaries")
	binPaths := buildMRPrograms(srcPaths, *flagMR, binOutPath, *flagCompiler)
	if err := runPrograms(binPaths); err != nil {
		panic(err)
	}
}
