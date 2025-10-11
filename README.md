# 🐚 PyShell — A Feature-Rich POSIX-Compatible Shell in Python

[![PyPI version](https://img.shields.io/pypi/v/pyshell-terminal.svg)](https://pypi.org/project/pyshell-terminal/)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

[![Website](https://img.shields.io/badge/Website-yogvidwankhede.com-blue)](https://yogvidwankhede.com)

[![GitHub Repo](https://img.shields.io/badge/GitHub-PyShell-black?logo=github)](https://github.com/yogvidwankhede/PyShell)

[![PyPI Project](https://img.shields.io/badge/PyPI-pyshell--terminal-orange?logo=pypi)](https://pypi.org/project/pyshell-terminal/)

---

A **feature-rich, POSIX-compatible shell** implemented in Python with advanced scripting capabilities.  
Cross-platform and extensible, PyShell brings the power of Unix-style scripting to Python environments.

---

## ✨ Features

- **POSIX Compatibility**: Standard shell syntax (`if`, `while`, `for`, `case`)
- **Advanced Arrays**: Indexed and associative arrays
- **Pipeline Support**: Full pipe, redirection, and background job control
- **Function Definitions**: Shell functions with local variables
- **Parameter Expansion**: `${var:-default}`, `${var#pattern}`, etc.
- **Command Substitution**: `$(command)` and backtick syntax
- **Arithmetic Expansion**: `$((expression))` with full math operations
- **Brace Expansion**: `{1..10}`, `{a,b,c}`
- **Glob Patterns**: `*`, `?`, `[...]` with extended matching
- **Built-in Commands**: 50+ built-ins (`cd`, `echo`, `export`, `test`, `local`, etc.)
- **Job Control**: Background jobs with `fg` / `bg`
- **History & Completion**: Command history with readline integration
- **Aliases**: Command aliasing support
- **Cross-Platform**: Works on Linux, macOS, and Windows

---

## 🚀 Installation

<<<<<<< HEAD
### From Source

```bash
git clone https://github.com/yogvidwankhede/PyShell.git
cd pyshell
pip install -e .
```

### Using pip (once published)
=======

```bash
pip install pyshell-terminal
```

### From Source

```bash
git clone https://github.com/yogvidwankhede/PyShell.git
cd PyShell
pip install -e .
```

---

## 📖 Usage

### Interactive Mode

```bash
python main.py
```

### Execute Command

```bash
python main.py -c "echo Hello World"
```

### Run Script

```bash
python main.py script.sh
```

---

## 💡 Examples

### Variables and Arrays

```bash
# Simple variables
name="PyShell"
echo $name

# Arrays
arr=(one two three)
echo ${arr[0]}
echo ${arr[@]}

# Associative arrays
declare -A config
config[host]="localhost"
config[port]=8080
echo ${config[host]}
```

### Control Flow

```bash
# If statements
if [ -f "file.txt" ]; then
    echo "File exists"
else
    echo "File not found"
fi

# Loops
for i in {1..5}; do
    echo "Count: $i"
done

# While loops
count=0
while [ $count -lt 5 ]; do
    echo $count
    count=$((count + 1))
done
```

### Functions

```bash
greet() {
    local name=$1
    echo "Hello, $name!"
}

greet "World"
```

### Pipelines and Redirection

```bash
# Pipes
cat file.txt | grep "pattern" | wc -l

# Redirection
echo "data" > output.txt
cat input.txt >> output.txt
command 2> errors.log
```

---

## 🏗️ Architecture

```
pyshell/
├── main.py           # Entry point and REPL
├── pyshell/
│   ├── tokenizer.py  # Lexical analysis
│   ├── parser.py     # Syntax analysis
│   ├── executor.py   # Command execution
│   ├── expansions.py # Variable/command expansion
│   ├── builtins.py   # Built-in commands
│   ├── state.py      # Global shell state
│   ├── ast_nodes.py  # AST node definitions
│   ├── exceptions.py # Custom exceptions
│   └── utils.py      # Utilities
└── tests/            # Test suite
```

---

## 🧪 Testing

```bash
python tests/run_all_tests.py
```

---

## 🤝 Contributing

Contributions are welcome! 🙌  

1. Fork the repository  
2. Create a feature branch  
   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. Commit your changes  
   ```bash
   git commit -m "Add some AmazingFeature"
   ```
4. Push to your branch  
   ```bash
   git push origin feature/AmazingFeature
   ```
5. Open a Pull Request

---

## 📝 Roadmap

- [ ] Tab completion improvements  
- [ ] More POSIX test operators  
- [ ] Process substitution  
- [ ] Co-processes  
- [ ] Additional shell options  
- [ ] Performance optimizations  

---


## 🙏 Acknowledgments

- Inspired by **Bash**, **Zsh**, and other Unix shells  
- Built using **Python’s `readline`** and **`subprocess`** modules  
