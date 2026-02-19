from pprint import pprint
import os

def getListOfFiles(dirName):
    # create a list of file and sub directories
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for fileName in listOfFile:
        fullPathWithFileName = os.path.join(dirName, fileName)
        # If entry is a directory then get the list of files in this directory
        if os.path.isdir(fullPathWithFileName):
            allFiles = allFiles + getListOfFiles(fullPathWithFileName)
        else:
            allFiles.append(fullPathWithFileName)
    return allFiles


def load_cobol_file(filePath):
    """
    Reads a COBOL file, processes it, and returns a dictionary containing
    the line number and file data.
    """
    fileName = filePath.split("/")[-1].split("\\")[-1].split(".")[0]
    file_data = {"program": fileName, "lines": {}}
    with open(filePath, "r") as f:
        for line_num, line_content in enumerate(f, 1):
            file_data["lines"][line_num] = line_content.strip()
    return file_data


def load_json_file(file_path):
    """Load a JSON file and return the parsed object (dict/list)."""
    import json

    with open(file_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_annotation_files(program_name, base_dir):
    """Load annotation JSONs for a given program from the assets folder.

    Returns a tuple (structure_annotation, business_annotation) where each may be
    a dict or None if not found.
    """
    struct_path = os.path.join(base_dir, "Annotated data", f"{program_name}.json")
    biz_path = os.path.join(base_dir, "Business Logic", f"{program_name}.json")

    struct = None
    biz = None
    if os.path.exists(struct_path):
        struct = load_json_file(struct_path)
    if os.path.exists(biz_path):
        biz = load_json_file(biz_path)
    return struct, biz

def processCobolFileData(file_data):
    """
    Processes the COBOL file data and returns a structured representation.
    """
    processed_data = {}
    for line_num, content in file_data.items():
        # Example processing: just store the length of each line
        processed_data[line_num] = {
            "content": content,
            "length": len(content)
        }
    return processed_data


def load_all_programs(cobol_dir: str, annotations_base: str):
    """Load all COBOL programs from `cobol_dir` and their annotations.

    Returns a list of dicts with keys: program, cobol (as returned by load_cobol_file),
    structure_annotation, business_annotation.
    """
    programs = []
    for path in getListOfFiles(cobol_dir):
        if not path.lower().endswith(('.cob', '.cbl', '.cpy')):
            continue
        cobol = load_cobol_file(path)
        program = cobol.get("program")
        struct, biz = load_annotation_files(program, annotations_base)
        programs.append({
            "program": program,
            "cobol_path": path,
            "cobol": cobol,
            "structure_annotation": struct,
            "business_annotation": biz,
        })
    return programs
