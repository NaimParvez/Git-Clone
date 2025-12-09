# PyGit - A Git Implementation in Python

A lightweight implementation of Git version control system written in pure Python. This project recreates the core functionality of Git, demonstrating how Git works under the hood.

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Core Concepts](#core-concepts)
- [Installation & Setup](#installation--setup)
- [Commands](#commands)
- [Usage Examples](#usage-examples)
- [Architecture](#architecture)
- [References](#references)

---

## Features

- **Initialize repositories** - Create a new `.pygit` directory structure
- **Stage files** - Add files/directories to the staging area (index)
- **Commit changes** - Create snapshots of your project with commit messages
- **Branching** - Create, switch, and delete branches
- **Checkout** - Switch between branches and restore files
- **View history** - Display commit logs with history
- **Status tracking** - See staged, unstaged, untracked, and deleted files

---

## Project Structure

```
d:\HUdai\Git-Clone\
├── main.py          # Main implementation with all Git functionality
├── README.md        # Documentation (this file)
└── hello.txt        # Sample file
```

### Internal `.pygit` Directory Structure

When you initialize a repository, PyGit creates:

```
.pygit/
├── objects/         # Stores all Git objects (blobs, trees, commits)
│   └── [hash]/      # Objects organized by first 2 chars of SHA-1
├── refs/            # References to commits
│   └── heads/       # Branch pointers
├── HEAD             # Current branch reference
└── index            # Staging area (JSON format)
```

---

## Core Concepts

### Git Objects


The system uses three main object types:

#### 1. **Blob** (Binary Large Object)

- Represents file content
- Created for each file you add
- Identified by SHA-1 hash of content
- `Mode: 100644` (regular file)

#### 2. **Tree**

- Represents directory structure
- Contains references to blobs and sub-trees
- Recursively defines the project structure
- `Mode: 40000` (directory)

#### 3. **Commit**

- Snapshot of the project at a point in time
- Contains:
  - Tree hash (project structure)
  - Parent hash(es) (previous commit(s))
  - Author information
  - Timestamp
  - Commit message

### Hashing

All objects are identified by their SHA-1 hash:

```
header = f"{type} {size}\0"
hash = SHA-1(header + content)
```

This ensures integrity and allows Git to detect changes.

---

## Installation & Setup

### Prerequisites

- Python 3.8 or higher

### Getting Started

1. Navigate to your project directory
2. Run PyGit commands using: `python main.py <command> [options]`

### Initialize a Repository

```bash
python main.py init
```

**Output:**

```
Initialized empty repository in ./.pygit
```

**What it does:**

- Creates `.pygit` directory structure
- Initializes `HEAD` pointing to `master` branch
- Creates empty index file
- Ready for adding files

---

## Commands

### 1. `init` - Initialize Repository

**Usage:**

```bash
python main.py init
```

**Implementation Details:**

- Creates `.pygit` directory and subdirectories
- Writes initial HEAD file: `ref: refs/heads/master\n`
- Saves empty index (staging area)
- Returns `False` if repository already exists

**Code Location:** `Repository.init()` (lines 181-197)

---

### 2. `add` - Stage Files

**Usage:**

```bash
python main.py add <file_or_directory> [<file_or_directory> ...]
```

**Examples:**

```bash
# Add a single file
python main.py add hello.txt

# Add a directory
python main.py add src/

# Add multiple files
python main.py add file1.txt file2.txt dir/
```

**Implementation Details:**

**For Files:** `Repository.add_file()`

- Reads file content as bytes
- Creates a Blob object from content
- Stores blob in `.pygit/objects/`
- Updates index file with `filepath -> blob_hash` mapping
- Prints confirmation message

**For Directories:** `Repository.add_directory()`

- Recursively walks through all files
- Skips `.pygit` and `.git` directories
- Creates Blob for each file
- Updates index with all file paths and hashes
- Reports number of files added

**Code Location:** Lines 209-279

---

### 3. `commit` - Create Snapshot

**Usage:**

```bash
python main.py commit -m "<message>" [--author "<name> <email>"]
```

**Examples:**

```bash
# Basic commit
python main.py commit -m "Initial commit"

# With custom author
python main.py commit -m "Fix bug" --author "John Doe <john@example.com>"

# Default author (if not specified)
# Anonymous <user@pygit>
```

**Implementation Details:** `Repository.commit()`

1. **Create Tree from Index**

   - Reads current index (staging area)
   - Builds nested directory structure
   - Creates Tree objects recursively
   - Returns root tree hash

2. **Get Parent Commit**

   - Reads current branch file
   - Gets latest commit hash on this branch

3. **Check for Changes**

   - Compares new tree with previous tree
   - Prevents empty commits (no changes)

4. **Create Commit Object**

   - Combines: tree hash, parent hash, author, message, timestamp
   - Serializes as standardized format

5. **Store & Update Reference**
   - Stores commit object in `.pygit/objects/`
   - Updates branch file with new commit hash
   - Clears index for next staging cycle

**Commit Object Format:**

```
tree <tree_hash>
parent <parent_hash>
author <name> <timestamp> +0000
commiter <name> <timestamp> +0000

<commit message>
```

**Code Location:** Lines 353-404

---

### 4. `checkout` - Switch Branches

**Usage:**

```bash
# Switch to existing branch
python main.py checkout <branch_name>

# Create and switch to new branch
python main.py checkout <branch_name> -b
python main.py checkout -b <branch_name>  # Alternative
```

**Examples:**

```bash
# Switch to existing branch
python main.py checkout develop

# Create new branch from current commit
python main.py checkout feature -b

# Create and switch
python main.py checkout -b experimental
```

**Implementation Details:** `Repository.checkout()`

1. **Calculate Files to Remove**

   - Gets files in current branch's latest commit
   - Determines which files need to be deleted

2. **Validate/Create Target Branch**

   - Checks if branch exists
   - Creates new branch from current commit if `-b` flag used
   - Fails if branch doesn't exist and no `-b` flag

3. **Update HEAD**

   - Updates `.pygit/HEAD` to point to new branch

4. **Restore Working Directory**
   - Removes files tracked by old branch
   - Extracts and writes files from new branch's commit
   - Clears index

**Code Location:** Lines 431-475

---

### 5. `branch` - Manage Branches

**Usage:**

```bash
# List all branches
python main.py branch

# Create new branch
python main.py branch <branch_name>

# Delete branch
python main.py branch <branch_name> -d
python main.py branch <branch_name> --delete
```

**Examples:**

```bash
# List all branches (shows * for current)
python main.py branch
# Output:
#   develop
# * master
#   feature

# Create new branch from current commit
python main.py branch staging

# Delete branch
python main.py branch old-branch -d
```

**Implementation Details:** `Repository.branch()`

**List Branches:**

- Reads all files in `.pygit/refs/heads/`
- Marks current branch with `*`
- Displays in sorted order

**Create Branch:**

- Gets current branch's latest commit
- Creates new branch file with same commit hash
- Fails if no commits exist

**Delete Branch:**

- Removes branch file from `.pygit/refs/heads/`
- Prevents deletion with error message if branch doesn't exist

**Code Location:** Lines 518-555

---

### 6. `log` - View Commit History

**Usage:**

```bash
python main.py log [-n <number>]
python main.py log [--number <number>]
```

**Examples:**

```bash
# Show last 10 commits (default)
python main.py log

# Show last 5 commits
python main.py log -n 5

# Show all commits
python main.py log -n 100
```

**Output Format:**

```
Commit: <commit_hash>
Author: <author_name>
Date: <YYYY-MM-DD HH:MM:SS>

    <commit message>

Commit: <parent_commit_hash>
...
```

**Implementation Details:** `Repository.log()`

1. Gets current branch's latest commit
2. Traverses commit history following parent pointers
3. For each commit:
   - Loads commit object from storage
   - Extracts and displays:
     - Commit hash
     - Author name
     - Formatted timestamp
     - Commit message
4. Stops after displaying specified number of commits
5. Follows first parent in case of merges

**Code Location:** Lines 558-582

---

### 7. `status` - Check Repository Status

**Usage:**

```bash
python main.py status
```

**Output Example:**

```
On branch master

Changes to be committed:
  added new file: file1.txt
  modified: file2.txt

Changes not staged for commit:
  modified: file3.txt

Untracked files:
  new_file.txt

Deleted files:
  deleted: removed.txt

Nothing to commit, working tree clean
```

**Implementation Details:** `Repository.status()`

1. **Get Current State**

   - Reads current branch name
   - Gets current commit from branch file
   - Loads index (staging area)

2. **Build Tree Index**

   - If commit exists, extracts file tree
   - Creates index of files in last commit

3. **Scan Working Directory**

   - Lists all files (excluding `.pygit`)
   - Computes blob hash for each file
   - Maps file path to hash

4. **Categorize Files**

   **Staged for Commit:**

   - In index but not in last commit (new files)
   - In both but different hash (modified)

   **Not Staged:**

   - In index but different from working directory
   - Means file was modified after staging

   **Untracked:**

   - In working directory but not in index or last commit
   - Never been committed

   **Deleted:**

   - In index but not in working directory
   - Was staged for deletion

**Code Location:** Lines 585-680

---

## Usage Examples

### Basic Workflow

```bash
# 1. Initialize repository
python main.py init

# 2. Create/modify files
echo "Hello World" > hello.txt
echo "print('test')" > script.py

# 3. Stage files
python main.py add hello.txt script.py

# 4. Check status
python main.py status

# 5. Commit changes
python main.py commit -m "Initial commit"

# 6. View history
python main.py log

# 7. Make more changes
echo "Updated content" >> hello.txt

# 8. Check status (unstaged changes)
python main.py status

# 9. Stage and commit
python main.py add hello.txt
python main.py commit -m "Update hello.txt"
```

### Branching Workflow

```bash
# Create new feature branch
python main.py checkout feature -b

# Make changes and commit
echo "new feature" > feature.txt
python main.py add feature.txt
python main.py commit -m "Add feature"

# List branches
python main.py branch

# Switch back to master
python main.py checkout master

# View commits on feature branch
python main.py checkout feature
python main.py log

# Delete feature branch
python main.py branch feature -d
```

---

## Architecture

### Class Hierarchy

```
GitObject (Abstract)
├── Blob (file content)
├── Tree (directory structure)
└── Commit (snapshot)

Repository
├── initialize repo
├── manage objects
├── manage index/staging
├── manage branches
├── handle checkout/restore
└── track status
```

### Key Methods by Class

**GitObject:**

- `hash()` - Compute SHA-1 hash
- `serialize()` - Compress with zlib
- `deserialize()` - Decompress object

**Blob:**

- `get_content()` - Return file bytes

**Tree:**

- `add_entry()` - Add file/directory reference
- `from_content()` - Parse binary tree format

**Commit:**

- `_serialize_commit()` - Format commit data
- `from_content()` - Parse commit data

**Repository:**

- `init()` - Initialize repository
- `add_file()/add_directory()/add_path()` - Stage files
- `commit()` - Create snapshot
- `checkout()` - Switch branches
- `branch()` - Manage branches
- `log()` - Show history
- `status()` - Show repository state
- `load_object()/store_object()` - Persist objects
- `load_index()/save_index()` - Manage staging area

### Data Flow

```
File System
    ↓
add_path()
    ↓
Blob Creation
    ↓
store_object() → .pygit/objects/
    ↓
Update index → .pygit/index
    ↓
commit()
    ↓
Tree Creation (from index)
    ↓
Commit Creation (tree + parent + message)
    ↓
store_object() → .pygit/objects/
    ↓
Update branch file → .pygit/refs/heads/branch_name
```

---

## Technical Details

### Index Format

The index is stored as JSON mapping file paths to blob hashes:

```json
{
  "hello.txt": "abc123...",
  "src/main.py": "def456...",
  "docs/readme.md": "ghi789..."
}
```

### Object Storage

Objects are stored in `.pygit/objects/` with directory structure based on hash prefix:

```
.pygit/objects/
├── ab/
│   └── c123...  (blob, tree, or commit)
├── de/
│   └── f456...
└── gh/
    └── i789...
```

### Serialization Format

**Tree Entry Format:**

```
<mode> <name>\0<20_byte_hash>
```

**Commit Format:**

```
tree <hash>
parent <hash>  (can be multiple)
author <name> <timestamp> +0000
commiter <name> <timestamp> +0000

<message>
```

---

## References

- Learn more about Git internals: https://blog.meain.io/2023/what-is-in-dot-git/
- Official Git documentation: https://git-scm.com/docs

---

## Notes

- This is an educational implementation showing Git concepts
- Not intended for production use
- Uses `.pygit` instead of `.git` to avoid conflicts with real Git
- Follows Git's architecture and storage model closely
