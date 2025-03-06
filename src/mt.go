// Description: Insert MR implementation into C source code and build the program
package main

import (
	"bytes"
	"context"
	"flag"
	"fmt"
	"io"
	"log"
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
		return fmt.Errorf("failed to start QEMU: %w", err)
	}

	// 将qemu进程ID写入文件
	qemu.pid = cmd.Process.Pid
	qemu.pidf = filepath.Join(*flagOut, "qemu.pid")
	qemu.inst = *cmd
	if err := os.WriteFile(qemu.pidf, []byte(fmt.Sprint(qemu.pid)), 0666); err != nil {
		return fmt.Errorf("failed to write QEMU PID to file: %w", err)
	}
	return nil
}

// 停止Qemu
func (qemu *Qemu) stop() error {
	// 杀死QEMU进程
	err := qemu.inst.Process.Kill()
	if err != nil {
		return fmt.Errorf("failed to stop QEMU: %w", err)
	}

	// 等待资源释放
	qemu.inst.Wait()
	return nil
}

// 重启Qemu
func (qemu *Qemu) restart() error {
	// 停止Qemu
	if err := qemu.stop(); err != nil {
		return fmt.Errorf("failed to restart QEMU: %w", err)
	}

	// 启动Qemu
	if err := qemu.boot(); err != nil {
		return fmt.Errorf("failed to restart QEMU: %w", err)
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
		return stdout, stderr, fmt.Errorf("failed to run SSH command: %w", err)
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
		return fmt.Errorf("failed to run SCP command: %w", err)
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
//
// Returns:
//
//	返回插入MR实现后的C代码内容, 以字节切片形式返回
func insertMRImpl(csrcPath string, mrPath string) []byte {
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

	// 获取main函数中系统调用行号切片
	lSlice := getSyscallLinenos(csrcPath)
	lSlice = lSlice[3:] // 使用syz-prog2c后前3个系统调用固定是syscall(__NR_mmap, ...), 去掉前三个系统调用

	// 将[#include "/path/to/mr.h"]插入到最后#include的行之后
	mrInclude := fmt.Sprintf("\n#include \"%s\"", mrPath)
	csrcSlice[lastIncludeLine] += mrInclude
	randIndex := rng.IntN(len(lSlice))
	csrcSlice[lSlice[randIndex]-1] += "\n\tMR();"

	// 将插入MR实现后的C代码内容按字节切片返回
	return []byte(strings.Join(csrcSlice, "\n"))
}

// 将内容写入指定文件中
func writeFile(content []byte, path string) error {
	err := os.WriteFile(path, content, 0666)
	if err != nil {
		return fmt.Errorf("failed to write file: %w", err)
	}
	return nil
}

// 将C代码编译为可执行文件
//
// Parameters:
//
//	srcPath: C代码文件
//	binPath: 可执行文件路径
//	compiler: 编译器
//
// Returns:
//
//	若编译成功, 返回nil; 否则返回错误信息
func buildProgram(srcPath string, binPath string, compiler string) error {
	var stdout, stderr bytes.Buffer
	cmd := exec.Command(compiler, "-static", "-o", binPath, srcPath)
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("failed to build program: %w\nSTDERR: %s", err, stderr.String())
	}
	return nil
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
		return fmt.Errorf("failed to write PC to file: %w", err)
	}

	// 删除可执行文件
	_, _, err = vm.ssh.run("rm /" + filepath.Base(binPath))
	if err != nil {
		return fmt.Errorf("failed to delete %s in vm: %w", filepath.Base(binPath), err)
	}

	return nil
}

func initVM() (*VM, error) {
	// 创建VM实例
	log.Printf("Creating VM instance")
	vm, err := create()
	if err != nil {
		return nil, fmt.Errorf("failed to create vm instance: %w", err)
	}

	// 启动qemu
	log.Printf("Booting VM instance")
	err = vm.qemu.boot()
	if err != nil {
		return nil, fmt.Errorf("failed to boot vm instance: %w", err)
	}

	// 与qemu进行交互, 查看能否连接成功
	time.Sleep(5 * time.Second)
	log.Printf("Handshaking with VM via ssh")
	_, _, err = vm.ssh.run("pwd")
	if err != nil {
		return nil, fmt.Errorf("failed to handshake with vm instance: %w", err)
	}

	// 将kcovtrace拷贝到qemu中
	log.Printf("Copy kcovtrace binary to VM")
	mtBin, _ := os.Executable()
	kcovtraceBin := filepath.Join(filepath.Dir(mtBin), "kcovtrace")
	err = vm.scp.run(kcovtraceBin, "localhost:/kcovtrace")
	if err != nil {
		return nil, fmt.Errorf("failed to copy kcovtrace binary to vm instance: %w", err)
	}

	return vm, nil
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
	os.Mkdir(filepath.Join(*flagOut, "csrc"), 0777)     // 存储插入MR实现的C源码的文件夹
	os.Mkdir(filepath.Join(*flagOut, "binaries"), 0777) // 存储插入MR实现且编译后的可执行文件的文件夹
	os.Mkdir(filepath.Join(*flagOut, "pc"), 0777)       // 存储可执行文件覆盖PC的文件夹

	// 设置日志文件
	logPath := filepath.Join(*flagOut, "run.log")
	logFile, err := os.OpenFile(logPath, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		panic(err)
	}
	defer logFile.Close()
	multiWriter := io.MultiWriter(os.Stdout, logFile) // 多路输出, 同时输出到标准输出和日志文件
	log.SetOutput(multiWriter)
	log.SetFlags(log.Ldate | log.Ltime | log.Lshortfile)
	log.Printf("Start running.")

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

	// 启动一个虚拟机
	vm, err := initVM()
	if err != nil {
		log.Fatalf("Failed to boot VM: %v", err)
		panic(err)
	}
	defer vm.qemu.stop()

	// 遍历每个源码路径, 插入MR->编译->运行
	for i, srcPath := range srcPaths {
		log.Printf("Insert, build, and execute. Source file: %s. Progress %d/%d.", filepath.Base(srcPath), i+1, len(srcPaths))

		// 将MR插入源文件
		log.Printf("Inserting ...")
		nSrcFn := strings.TrimSuffix(filepath.Base(srcPath), ".c") + "-mr.c" // New Source Filename
		nPath := filepath.Join(*flagOut, "csrc", nSrcFn)
		nSrc := insertMRImpl(srcPath, *flagMR)
		err = writeFile(nSrc, nPath)
		if err != nil {
			log.Fatalf("Failed to insert MR into %s: %v", filepath.Base(srcPath), err)
			panic(err)
		}

		// 编译新的C代码为可执行文件
		log.Printf("Building ...")
		binFn := strings.TrimSuffix(filepath.Base(srcPath), ".c") + "-mr" // Binary Filename
		binPath := filepath.Join(*flagOut, "binaries", binFn)
		err = buildProgram(nPath, binPath, *flagCompiler)
		if err != nil {
			log.Fatalf("Failed to build %s: %v", binFn, err)
			panic(err)
		}

		// 将编译后的可执行文件复制到vm
		log.Printf("Copying ...")
		err = vm.scp.run(binPath, "localhost:/"+filepath.Base(binPath))
		if err != nil {
			log.Fatalf("Failed to copy %s to vm: %v", filepath.Base(binPath), err)
			panic(err)
		}

		// 尝试运行可执行文件3次, 若失败则重启qemu后再尝试3次
		log.Printf("Executing ...")
		pass := false
		for j := 0; j < 3; j++ {
			err = runProgram(vm, binPath)
			if err == nil {
				pass = true
				break
			}
		}

		// 成功了, 继续下一个测试用例; 失败了, 重启qemu后再尝试3次
		if pass {
			continue
		}
		log.Printf("Restarting qemu and retrying %s", filepath.Base(binPath))
		vm.qemu.restart()
		time.Sleep(5 * time.Second)
		if _, _, err := vm.ssh.run("pwd"); err != nil {
			log.Fatalf("Failed to handshake with VM after restart: %v", err)
			panic(err)
		}

		for j := 0; j < 3; j++ {
			err = runProgram(vm, binPath)
			if err == nil {
				pass = true
				break
			}
		}

		// 仍然失败, 跳过这个测试用例, 打印信息
		if !pass {
			log.Printf("Shit, run %s failed, skip it.", filepath.Base(binPath))
		}
	}
	log.Printf("All done.")
}
