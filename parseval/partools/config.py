import yaml


with open('./config.yaml', 'r', encoding='utf8') as f:
    CONFIG = yaml.safe_load(f)

if __name__ == "__main__":
    print(CONFIG)
