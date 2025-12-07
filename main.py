from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Dict, List, Tuple
import zlib




class GitObject:
    def __init__(self, obj_type: str, content: bytes):
        self.type = obj_type
        self.content = content

    def hash(self) -> str:
        # <type> <size of content>\0<content>  ; type= commit/blob/tree/tags
        header = (
            f"{self.type} {len(self.content)}\0".encode()
        )  # type and size is separated by a space . it will be helpful in deserialize
        return hashlib.sha1(header + self.content).hexdigest()

    def serialize(self) -> bytes:  # compress
        header = f"{self.type} {len(self.content)}\0".encode()
        return zlib.compress(header + self.content)

    # decompress
    @classmethod
    def deserialize(
        cls, data: bytes
    ) -> (
        "GitObject"
    ):  # we can do GitObject also instead "GitObject" for that use (from __future__ import annotations)
        decompressed = zlib.decompress(data)  # byte string
        null_idx = decompressed.find(b"\0")
        header = decompressed[:null_idx]
        content = decompressed[null_idx + 1 :]

        obj_type, size = header.split(" ")

        return cls(obj_type, content)


class Blob(GitObject):
    def __init__(self, content: bytes):
        super().__init__("blob", content)

    def get_content(self) -> bytes:
        return self.content


class Tree(GitObject):
    def __init__(self, entries: List[Tuple[str, str, str]] = None):
        self.entries = entries or []  # list of tuples (mode, name, obj_hash)
        content = self._serialize_entries()
        super().__init__("tree", content)

    def _serialize_entries(self) -> bytes:
        # serialize the entries into bytes
        # <mode> <name>\0<obj_hash>
        content = b""
        for mode, name, obj_hash in sorted(self.entries):
            entry = f"{mode} {name}\0".encode() + bytes.fromhex(obj_hash)
            content += entry
        return content
    
    def add_entry(self, mode: str, name: str, obj_hash: str):
        self.entries.append((mode, name, obj_hash))
        self.content = self._serialize_entries()
        
     # decompress
    @classmethod
    def from_content(cls, content: bytes) -> Tree: 
        tree = cls([])
        idx = 0
        
        while idx < len(content):
            null_idx = content.find(b"\0", idx)
            if null_idx == -1:
                break
            mode_name = content[idx:null_idx].decode()
            mode, name = mode_name.split(" ", 1)
            obj_hash = content[null_idx + 1 : null_idx + 21].hex() # SHA-1 hash is 20 bytes
            tree.entries.append((mode, name, obj_hash))
            
            idx = null_idx + 21
        return tree
            
class Commit(GitObject):
    def __init__(
        self,
        tree_hash: str,
        parent_hash: List[str],# can be multiple parents in case of merge
        author: str,
        commiter:str,
        message: str,
        timestamp: int = None,       
    ):
        self.tree_hash = tree_hash
        self.parent_hash = parent_hash
        self.author = author
        self.commiter=commiter
        self.message = message
        self.timestamp = timestamp or int(time.time())
        
        content = self._serialize_commit()
        super().__init__("commit", content)
        
        
    def _serialize_commit(self):
        # serialize commit content
        # tree <tree_hash>\n
        # parent <parent_hash>\n (multiple parents possible)
        lines = [f"tree {self.tree_hash}"]
        for parent in self.parent_hash:
            lines.append(f"parent {parent}")
            
        lines.append(f"author {self.author} {self.timestamp} +0000")
        lines.append(f"commiter {self.commiter} {self.timestamp} +0000")
        lines.append("")  # blank line before message
        lines.append(self.message)
        content = "\n".join(lines).encode() 
        return content
    
    @classmethod
    def from_content(cls, content: bytes) -> Commit:
        lines = content.decode().split("\n")
        tree_hash =None
        parent_hash = [] # can be multiple parents in case of merge
        author = None
        commiter = None
        message_start = 0
        
        for i, line in enumerate(lines):
            if line.startswith("tree "):
                tree_hash = line[5:]
            elif line.startswith("parent "):
                parent_hash.append(line[7:]) # can be multiple parents in case of merge
            elif line.startswith("author "):
                author_parts = line[7:].rsplit(" ",2)
                author = author_parts[0]
                timestamp = int(author_parts[1])
            elif line.startswith("commiter "):
                commiter = line[9:].rsplit(" ",2)[0]
            elif line == "":
                message_start = i + 1
                break
        message = "\n".join(lines[message_start:])
        return cls(tree_hash, parent_hash, author, commiter, message,timestamp)

class Repository:
    def __init__(self, path="."):  # path="." means current folder or file we are in
        self.path = Path(
            path
        ).resolve()  # path should not be relative , we need absolute path. resolve do that
        self.git_dir = (
            self.path / ".pygit"
        )  # since the real git also create .git so to be different we named .pygit

        # .git/objects  dir
        self.objects_dir = self.git_dir / "objects"  # creating object dir to store
        # .git/refs dir
        self.ref_dir = self.git_dir / "refs"  # creating object dir to store
        self.heads_dir = self.ref_dir / "heads"
        # .git/HEAD  file
        self.head_file = self.git_dir / "HEAD"  # creating object dir to store
        # .git/index  file
        self.index_file = self.git_dir / "index"  # creating index dir to handle staging

    def init(self) -> bool:

        if self.git_dir.exists():
            return False

        # create directories
        self.git_dir.mkdir()
        self.objects_dir.mkdir()
        self.ref_dir.mkdir()
        self.heads_dir.mkdir()

        # create initial HEAD pointing to a branch
        self.head_file.write_text("ref: refs/heads/master\n")

        self.save_index({})

        print(f"Initialized empty repository in {self.git_dir}")

        return True

    def store_object(self, obj: GitObject):  # store git object and commits as well
        obj_hash = obj.hash()
        obj_dir = (
            self.objects_dir / obj_hash[:2]
        )  # 1st two digit of the hash is directory and rest will the file name inside that dir
        obj_file = obj_dir / obj_hash[2:]

        if not obj_file.exists():
            obj_dir.mkdir(
                exist_ok=True
            )  # means if the directory already exists, don't error out
            obj_file.write_bytes(obj.serialize())

        return obj_hash

    def load_index(self) -> Dict[str, str]:
        if not self.index_file.exists():
            return {}

        try:
            return json.loads(self.index_file.read_text())
        except:
            return {}

    def save_index(self, index: Dict[str, str]):
        self.index_file.write_text(json.dumps(index, indent=2))

    def add_file(self, path: str):
        # Read the file content
        full_path = self.path / path
        if not full_path.exists():
            raise FileExistsError(f"Path {full_path} not found")

        content = full_path.read_bytes()
        # Create BLOB object from the content
        blob = Blob(content)
        # Store the blob object in database(.git/object)
        blob_hash = self.store_object(blob)
        # Update the index to include the file
        index = (
            self.load_index()
        )  # load the index file(assume index file as a database)
        index[path] = blob_hash  # add the file hash
        self.save_index(index)  # again save the index file

        print(f"{path} Added")

    def add_directory(self, path: str):

        full_path = self.path / path
        if not full_path.exists():
            raise FileExistsError(f"Directory {full_path} not found")

        if not full_path.is_dir():
            raise ValueError(f"{path} is not a Directory")

        index = self.load_index()
        added_count = 0
        # Recursively traverse the directory
        for file_path in full_path.rglob(
            "*"
        ):  # Recursively yield all existing files (of any kind, including directories) matching the given relative pattern, anywhere in this subtree
            if file_path.is_file():
                if ".pygit" in file_path.parts or ".git" in file_path.parts:
                    continue

                # create & store blob object
                content = file_path.read_bytes()
                blob = Blob(content)
                blob_hash = self.store_object(blob)

                # update index
                rel_path = str(file_path.relative_to(self.path))
                index[rel_path] = blob_hash
                added_count += 1

        self.save_index(index)

        if added_count > 0:
            print(f"Added {added_count} files from directory {path}")
        else:
            print(f"Directory {path} is already up to date")
        # Create blob objects for all files
        # Store all blobs in the object database (.git/objects)
        # Update the index to include all the files
        pass

    def add_path(self, path: str) -> None:
        full_path = (
            self.path / path
        )  # 1st path is from the resolver(current directory) and the 2nd path the file od directory we give

        if not full_path.exists():
            raise FileExistsError(f"Path {full_path} not found")

        if full_path.is_file():
            self.add_file(path)
        elif full_path.is_dir():
            self.add_directory(path)
        else:
            raise ValueError(f"{path} is neither a file or a directory")

    def load_object(self, obj_hash: str) -> GitObject:
        obj_dir = self.objects_dir / obj_hash[:2] 
        obj_file = obj_dir / obj_hash[2:]
        if not obj_file.exists():
            raise FileNotFoundError(f"Object {obj_hash} not found")
        
        return GitObject.deserialize(obj_file.read_bytes())

    def create_tree_from_index(self):
        index = self.load_index()
        if not index:
            tree = Tree()
            raise self.store_object(tree)
        dirs = {}
        files ={}
        
        for file_path, blob_hash in index.items():
            parts=file_path.split("/")
            if len(parts)==1:
                # file in root dir
                files[parts[0]]=blob_hash
            else:
                dir_name=parts[0]
                if dir_name not in dirs:
                    dirs[dir_name]={}
                    
                current = dirs[dir_name]
                for part in parts[1:-1]:
                    if part not in current:
                        current[part]={}
                    current=current[part]
                    
                current[parts[-1]]=blob_hash
        
        def create_tree_recursive(entries_dict: Dict):
            tree = Tree()
            
            for name, blob_hash in entries_dict.items():
                if isinstance(blob_hash, str):
                    # it's a file
                    tree.add_entry("100644", name, blob_hash)
                if isinstance(blob_hash, dict):
                    # it's a directory
                    sub_tree_hash = create_tree_recursive(blob_hash)
                    tree.add_entry("40000", name, sub_tree_hash)
                    
            return self.store_object(tree)
        
        root_entries = {**files}
        for dir_name, dir_content in dirs.items():
            root_entries[dir_name]=dir_content

        return create_tree_recursive(root_entries)
    
    def get_current_branch(self) -> str:
        if not self.head_file.exists():
           return "master"
        head_content = self.head_file.read_text().strip()
        if head_content.startswith("ref: refs/heads/"):
           return head_content[16:]
        return "HEAD"
    
    def get_branch_commit(self, current_branch:str):
        branch_file = self.heads_dir / current_branch
        if not branch_file.exists():
          return None
        return branch_file.read_text().strip()
    def set_branch_commit(self, current_branch:str, commit_hash:str):
        branch_file = self.heads_dir / current_branch
        branch_file.write_text(commit_hash + "\n")
    
    def commit(self, message: str, author: str):
        # Create a tree object from the current index(staging area)
        tree_hash = self.create_tree_from_index()
        
        current_branch = self.get_current_branch()
        parent_commit = self.get_branch_commit(current_branch)
        parent_hash = [parent_commit] if parent_commit else []
        
        index = self.load_index() 
        if not index: # if index is empty , nothing to commit
            print("Nothing to commit, working tree clean")
            return None
        
        if parent_commit:
            parent_git_commit_obj = self.load_object(parent_commit)
            parent_commit_data = Commit.from_content(parent_git_commit_obj.content)
            if parent_commit_data.tree_hash == tree_hash:
                print("Nothing to commit, working tree clean")
                return None
            
        
        # Create a commit object
        commit = Commit(
            tree_hash=tree_hash,
            parent_hash=parent_hash,
            author=author,
            commiter=author,
            message=message,
        )
        
        commit_hash = self.store_object(commit)
        
        self.set_branch_commit(current_branch, commit_hash)
        
        self.save_index({}) # clear the index after commit to check next time if there is any change to commit
        print(f"Committed to {current_branch} with commit hash {commit_hash}")
        return commit_hash


def main():
    parser = argparse.ArgumentParser(description="pygit - A simple git clone ")
    subparser = parser.add_subparsers(dest="command", help="Available command")

    # suppoted commands

    # init
    init_parser = subparser.add_parser("init", help="Initialize a new repository")
    # add
    add_parser = subparser.add_parser(
        "add", help="Add files and directories to the staging area"
    )
    add_parser.add_argument("paths", nargs="+", help="Files and directories to add")

    commit_parser = subparser.add_parser(
        "commit", help="Commit the staged changes to the repository"
    )

    commit_parser.add_argument("-m", "--message", required=True, help="Commit message")
    commit_parser.add_argument("--author", help="Author name and email")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    repo = Repository()

    try:
        if args.command == "init":
            if not repo.init():
                print("Repository Already Exits")
                return
        elif args.command == "add":
            if not repo.git_dir.exists():
                print("No such repository exist !!")
                return

            for path in args.paths:
                repo.add_path(path)

        elif args.command == "commit":
            if not repo.git_dir.exists():
                print("No such repository exist !!")
                return
            author = args.author if args.author else "Anonymous <user@pygit>"
            repo.commit(args.message, author)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


main()
