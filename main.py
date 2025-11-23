import argparse
import json
from pathlib import Path
import sys


class Repository:
    def __init__(self,path="."):  #path="." means current folder or file we are in
        self.path =Path(path).resolve() # path should not be relative , we need absolute path. resolve do that
        self.git_dir = self.path / ".pygit" # since the real git also create .git so to be different we named .pygit

        #.git/objects  dir
        self.objects_dir = self.git_dir / "objects" # creating object dir to store 
        #.git/refs dir
        self.ref_dir = self.git_dir / "refs" # creating object dir to store 
        self.heads_dir =self.ref_dir / "heads"
        #.git/HEAD  file
        self.head_file = self.git_dir / "HEAD" # creating object dir to store 
        #.git/index  file
        self.index_file = self.git_dir / "index" # creating index dir to handle staging 
        
    def init(self)-> bool:
        
        if self.git_dir.exists():
            return False
        
        #create directories
        self.git_dir.mkdir()
        self.objects_dir.mkdir()
        self.ref_dir.mkdir()
        self.heads_dir.mkdir()
        
        #create initial HEAD pointing to a branch
        self.head_file.write_text("ref: refs/heads/master\n")
        
        self.index_file.write_text(json.dumps({},indent=2))
        
        print(f"Initialized empty repository in {self.git_dir}")
        
        return True
        

def main():
    parser = argparse.ArgumentParser(
        description="pygit - A simple git clone "
    )
    subparser =parser.add_subparsers(
        dest="command" ,
        help="Available command"
    )
    
    #init command
    init_parser = subparser.add_parser("init", help="Initialize a new repository")

    args =parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "init":
            repo = Repository()
            if not repo.init():
                print("Repository Already Exits")
                return
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
        

main()