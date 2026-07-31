import importlib.util

pkgs = ['chromadb', 'sentence_transformers', 'fastembed', 'faiss', 'sklearn', 'numpy', 'scipy', 'torch', 'tqdm']
for p in pkgs:
    spec = importlib.util.find_spec(p)
    if spec is not None:
        print(f"{p}: INSTALLED")
    else:
        print(f"{p}: NOT INSTALLED")
