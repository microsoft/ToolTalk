import os


def get_names_and_paths(input_path: str):
    if os.path.isdir(input_path):
        files = os.listdir(input_path)
        file_paths = [os.path.join(input_path, name) for name in files]
        file_names_and_paths = [(name, path) for name, path in zip(files, file_paths)]
        return file_names_and_paths
    elif os.path.isfile(input_path):
        return [(os.path.basename(input_path), input_path)]
    else:
        raise ValueError(f"Unknown input path: {input_path}")


def chunkify(lst, n):
    chunks = list()
    for i in range(0, len(lst), n):
        chunks.append(lst[i:i + n])
    return chunks
