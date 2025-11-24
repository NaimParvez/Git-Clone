import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Dict
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
    def deserialize(cls, data: bytes) -> "GitObject":  # we can do GitObject also instead "GitObject" for that use (from __future__ import annotations)
        decompressed = zlib.decompress(data)  # byte string
        null_idx = decompressed.find(b"\0")
        header = decompressed[:null_idx]
        content = decompressed[null_idx + 1 :]
        
        obj_type, size = header.split(" ")

        return cls(obj_type, content)


class Blob(GitObject):
    def __init__(self, content:bytes):
        super().__init__('blob', content)
        
    def get_content(self)-> bytes:
        return self.content


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
    
    def store_object(self, obj:GitObject): #store git object and commits as well
        obj_hash =obj.hash()
        obj_dir =self.objects_dir /obj_hash[:2]  # 1st two digit of the hash is directory and rest will the file name inside that dir
        obj_file = obj_dir / obj_hash[2:]
        
        if not obj_file.exists():
            obj_dir.mkdir(exist_ok=True) #means if the directory already exists, don't error out
            obj_file.write_bytes(obj.serialize())
            
        return obj_hash
            
    def load_index(self)->Dict[str, str]:
        if not self.index_file.exists():
            return {}
        
        try:
            return json.loads(self.index_file.read_text())
        except:
            return {}
        
    def save_index(self,index: Dict[str,str]):
        self.index_file.write_text(json.dumps(index, indent =2))
            
            
    def add_file(self, path: str):
        # Read the file content
        full_path = self.path / path
        if not full_path.exists():
            raise FileExistsError(f"Path {full_path} not found")
        
        content = full_path.read_bytes()
        # Create BLOB object from the content
        blob = Blob(content)
        # Store the blob object in database(.git/object)
        blob_hash =self.store_object(blob)
        # Update the index to include the file
        index=self.load_index()  #load the index file(assume index file as a database)
        index[path] =blob_hash # add the file hash
        self.save_index(index) # again save the index file
        
        print(f"{path} Added")
        
    def add_directory(self,path:str):
        
        full_path = self.path / path
        if not full_path.exists():
            raise FileExistsError(f"Directory {full_path} not found")
        
        if not full_path.is_dir():
            raise ValueError(f"{path} is not a Directory")
        
        index =self.load_index()
        added_count = 0
        # Recursively traverse the directory
        for file_path in full_path.rglob("*"):  #Recursively yield all existing files (of any kind, including directories) matching the given relative pattern, anywhere in this subtree
            if file_path.is_file():
                if ".pygit" in file_path.parts or ".git" in file_path.parts:
                    continue
                
                #create & store blob object 
                content = file_path.read_bytes()
                blob = Blob(content)
                blob_hash = self.store_object(blob)
                
                #update index
                rel_path = str(file_path.relative_to(self.path))
                index[rel_path]= blob_hash
                added_count+=1
                
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
        full_path = (self.path / path)  # 1st path is from the resolver(current directory) and the 2nd path the file od directory we give
        
        if not full_path.exists():
            raise FileExistsError(f"Path {full_path} not found")
        
        if full_path.is_file():
            self.add_file(path)
        elif full_path.is_dir():
            self.add_directory(path)
        else:
            raise ValueError(f"{path} is neither a file or a directory")


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

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


main()
