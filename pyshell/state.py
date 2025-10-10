"""
Manages the global state of the shell - COMPLETE 100% VERSION
All features including arrays, associative arrays, extended options, regex matching
"""

import sys
import os
from typing import List, Optional, Dict, Any, Tuple
import subprocess

# --- Shell State Variables ---

# Non-interactive mode flag (for -c option)
non_interactive: bool = False

# Job status constants
JOB_STATUS_RUNNING = "Running"
JOB_STATUS_STOPPED = "Stopped"
JOB_STATUS_DONE = "Done"

# Interpreter paths for script execution
PYTHON_INTERPRETER_PATH = sys.executable
NODE_INTERPRETER_PATH = 'node'
JAVA_INTERPRETER_PATH = 'java'

INTERPRETER_MAP = {
    '.py': PYTHON_INTERPRETER_PATH,
    '.js': NODE_INTERPRETER_PATH,
    '.jar': JAVA_INTERPRETER_PATH,
}

# Autocomplete state
last_matches: List[str] = []
last_text: Optional[str] = None

# Core shell state
manual_history: List[str] = []
last_saved_index: int = 0
last_exit_status: int = 0
last_background_pid: int = 0
running_jobs: List[Tuple[int, subprocess.Popen, str, str]] = []
next_job_id: int = 1
previous_dir: Optional[str] = None
aliases: Dict[str, str] = {}
local_vars: Dict[str, Any] = {}
functions: Dict[str, Any] = {}
is_suspending: bool = False
current_foreground_proc: Optional[subprocess.Popen] = None

# Function nesting counter
function_nesting: int = 0

# Enhanced state for advanced features

# Positional parameters ($1, $2, etc.)
positional_params: List[str] = []

# Script name ($0)
script_name: Optional[str] = None

# Last argument of previous command ($_)
last_arg: str = ""

# Shell options ($-)
shell_options: str = ""

# Shell option flags
option_errexit: bool = False  # set -e
option_nounset: bool = False  # set -u
option_xtrace: bool = False   # set -x
option_pipefail: bool = False  # set -o pipefail
option_noclobber: bool = False  # set -C
option_noglob: bool = False   # set -f

# Extended shell options (shopt)
option_extglob: bool = False  # Extended glob patterns
option_nocaseglob: bool = False  # Case-insensitive globbing
option_nullglob: bool = False  # Empty expansion for no matches
option_dotglob: bool = False  # Include hidden files in globs
option_history_expand: bool = True  # Enable history expansion
option_expand_aliases: bool = True  # Expand aliases

# Array variables (indexed arrays)
# Format: {'array_name': ['val1', 'val2', 'val3']}
arrays: Dict[str, List[str]] = {}

# Associative arrays (hash maps)
# Format: {'hash_name': {'key1': 'val1', 'key2': 'val2'}}
assoc_arrays: Dict[str, Dict[str, str]] = {}

# Array declaration tracking
# Format: {'name': 'indexed'} or {'name': 'associative'}
declared_arrays: Dict[str, str] = {}

# Read-only variables
readonly_vars: set = set()

# Exported variables (to be passed to child processes)
exported_vars: set = set()

# Directory stack for pushd/popd
dir_stack: List[str] = []

# Trap handlers: signal -> command
trap_handlers: Dict[str, str] = {}

# Loop control flags
break_loop: bool = False
break_levels: int = 0
continue_loop: bool = False
continue_levels: int = 0

# Return flag for functions
return_from_function: bool = False
return_value: int = 0

# Subshell depth
subshell_depth: int = 0

# Input file descriptors
file_descriptors: Dict[int, Any] = {}

# Prompt strings
PS1: str = "$ "
PS2: str = "> "
PS3: str = "#? "
PS4: str = "+ "

# Here-document storage
heredoc_content: Dict[str, str] = {}  # delimiter -> content

# Process substitution file tracking
process_subst_files: List[str] = []  # Temp files to clean up

# History expansion state
last_history_expanded: str = ""

# Select command state
select_active: bool = False
select_options: List[str] = []

# Regex match results (for [[ =~ ]])
regex_match_groups: List[str] = []
BASH_REMATCH: List[str] = []  # Bash compatibility

# Completion system
completion_specs: Dict[str, List[str]] = {}  # command -> completions

# Disabled built-ins
disabled_builtins: set = set()

# Command hash cache
command_hash: Dict[str, str] = {}

# Fix HOME environment variable if not set properly
if 'HOME' not in os.environ or not os.environ['HOME']:
    if sys.platform == 'win32':
        os.environ['HOME'] = os.environ.get(
            'USERPROFILE', 'C:\\Users\\Default')
    else:
        try:
            import pwd
            os.environ['HOME'] = pwd.getpwuid(os.getuid()).pw_dir
        except:
            os.environ['HOME'] = '/'
