# classify-my-dataset

A graphic user interface program to work with labels and images in a classification dataset.

# Configuration file

The program needs the `somename.classify.json` file, in this format:


    [
        {
            "button_label":"Positive",
            "short_cut": "1",
            "button_image":"/home/username/images/logo-happy.png",
            "button_image_width":32
        },
        {
            "button_label":"Neutral"
        },
        {
            "button_label":"Negative"
        }
    ]


The keys `short_cut`, `button_image` and `button_image_width` are optional. The quantity of buttons ever should be greater than 1.

The next text is an example of configuration file to tag using two types of labels `{Happy,Sad}`.

    [
        {
            "button_label":"Happy",
            "short_cut": "1",
            "button_image":"/home/username/images/logo-happy.png",
            "button_image_width":64
        },
        {
            "button_label":"Sad",
            "short_cut": "2",
            "button_image":"/home/username/images/logo-sad.png",
            "button_image_width":64
        }
    ]


* `short_cut` is the shortcut to activate the button with label `button_label`.
* `button_image` is the path of icon image of button with label `button_label`.
* `button_image_width` is the width at which the button icon will be displayed.

