# classify-my-dataset

A graphic user interface program to work with labels and images in a classification dataset.

![logo](screenshot.png)

## 1. Installing

To install the package from [PyPI](https://pypi.org/project/classify_my_dataset/), follow the instructions below:


```bash
pip install --upgrade classify_my_dataset
```

Execute `which classify-my-dataset` to see where it was installed, probably in `/home/USERNAME/.local/bin/classify-my-dataset`.

### Using

To start, use the command below:

```bash
classify-my-dataset
```

Later:

* Use a [somename.classify.json](doc/CLASSIFY.JSON.md) file in the following format to categorize "Happy" and "Sad":

```
[
    {
        "button_label":"Happy",
    },
    {
        "button_label":"Sad",
    }
]
```

* Use a `*.csv` file (ex: `dataset.csv`)  in the following format:
```
filepath, label
relative/path/to/image1.png,
relative/path/to/image2.png,Happy
relative/path/to/image3.png,
relative/path/to/image4.png,
```


## 2. More information

If you want more information go to [doc](https://github.com/trucomanx-desktop/ClassifyMyDataset/blob/main/doc) directory

## 3. Buy me a coffee

If you find this tool useful and would like to support its development, you can buy me a coffee!  
Your donations help keep the project running and improve future updates.  

[☕ Buy me a coffee](https://ko-fi.com/trucomanx) 

## 4. License

This project is licensed under the GPL license. See the `LICENSE` file for more details.
