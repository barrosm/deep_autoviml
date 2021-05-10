# deep_autoviml
## Build keras pipelines and models in a single line of code!
![banner](logo.jpg)
[![forthebadge made-with-python](http://ForTheBadge.com/images/badges/made-with-python.svg)](https://www.python.org/)
[![ForTheBadge built-with-love](http://ForTheBadge.com/images/badges/built-with-love.svg)](https://github.com/AutoViML)
[![standard-readme compliant](https://img.shields.io/badge/standard--readme-OK-green.svg?style=flat-square)](https://github.com/RichardLitt/standard-readme)
[![Python Versions](https://img.shields.io/pypi/pyversions/autoviml.svg?logo=python&logoColor=white)](https://pypi.org/project/autoviml)
[![Build Status](https://travis-ci.org/joemccann/dillinger.svg?branch=master)](https://github.com/AutoViML)
## Table of Contents
<ul>
<li><a href="#background">Background</a></li>
<li><a href="#features">Features</a></li>
<li><a href="#technology">Technology</a></li>
<li><a href="#install">Install</a></li>
<li><a href="#usage">Usage</a></li>
<li><a href="#api">API</a></li>
<li><a href="#tips">Tips for using deep_autoviml</a></li>
<li><a href="#maintainers">Maintainers</a></li>
<li><a href="#contributing">Contributing</a></li>
<li><a href="#license">License</a></li>
</ul>

## Background
- ✨ deep_autoviml is a powerful new deep learning library with a very simple design goal:  ✨
>           Make it as easy as possible for novices and 
>           experts alike to experiment with and build tensorflow.keras
>           preprocessing pipelines and models in as few lines of code
>           as possible.

deep_autoviml is a tensorflow >2.4-enabled, keras-ready, model and pipeline building utility.
deep autoviml is meant for data engineers, data scientists and ml engineers to quickly prototype and build tensorflow 2.4.1+ models and pipelines for any data set, any size using a single line of code.

![why_deep](deep_2.jpg)

## Features
These are the main features that distinguish deep_autoviml from other libraries:
- It uses keras preprocessing layers which are more intuitive, and are included inside your model to simplify deployment
- The pipeline is available to you to use as inputs in your own functional model (if you so wish - you must specify that option in the input - see below for "pipeline")
- It can import any csv, txt or gzip file or file patterns (that fit multiple files) and it can scale to any data set of any size due to tf.data.Dataset's superior data pipelining features (such as cache, prefetch, batch, etc.)
- It uses an amazing new tuner called [STORM tuner](https://github.com/ben-arnao/StoRM) that quickly searches for the best hyperparameters for your keras model in fewer than 25 trials
- If you want to fine tune your model even further, you can fiddle with a wide variety of model options or keras options using **kwargs like dictionaries
- You can import your own custom Sequential model and watch it transform it into a functional model with additional preprocessing and output layers and train the model with your data 
- You can save the model on your local machine or copy it to any cloud provider's storage bucket and serve it from there using tensorflow Serving (TF.Serving)
- Since your model contains preprocessing layers built-in, you just need to provide your Tensorflow serving model with raw data to test and get back predictions in the same format as your training labels.

![how_it_works](deep_1.jpg)

## Technology

deep_autoviml uses the latest in tensorflow (2.4.1+) td.data.Datasets and tf.keras preprocessing technologies: the Keras preprocessing layers enable you to encapsulate feature engineering and preprocessing into the model itself. This makes the process for training and predictions the same: just feed input data (in the form of files or dataframes) and the model will take care of all preprocessing before predictions. 

![how_deep](deep_4.jpg)

To perform its preprocessing on the model itself, deep_autoviml [tensorflow](https://www.tensorflow.org/) (TF 2.4.1+ and later versions) and [tf.keras](https://www.tensorflow.org/api_docs/python/tf/keras) experimental preprocessing layers: these layers are part of your saved model. They become part of the model's computational graph that can be optimized and executed on any device including GPU's and TPU's. By packaging everything as a single unit, we save the effort in reimplementing the preprocessing logic on the production server. The new model can take raw tabular data with numeric and categorical variables or strings text directly without any preprocessing. This avoids missing or incorrect configuration for the preprocesing_layer during production.

In addition, to select the best hyper parameters for the model, it uses a new open source library:
- [storm-tuner](https://github.com/ben-arnao/StoRM) - storm-tuner is an amazing new library that enables us to quickly fine tune our keras sequential models with hyperparameters and find a performant model within a few trials.

## Install

deep_autoviml requires [tensorflow](https://www.tensorflow.org/api_docs/python/tf) v2.4.1+ and [storm-tuner](https://github.com/ben-arnao/StoRM)  to run. Don't worry! We will install these libraries when you install deep_autoviml.

```sh
pip install deep_autoviml
```

For your own conda environment...

```
conda create -n <your_env_name> python=3.7 anaconda
conda activate <your_env_name> # ON WINDOWS: `source activate <your_env_name>`
pip install deep_autoviml
or
pip install git+https://github.com/AutoViML/deep_autoviml.git
```

## Usage

deep_autoviml can be invoked with a simple import and run statement:

```
from deep_autoviml import deep_autoviml as deepauto
```

Load a data set (any .csv or .gzip or .gz or .txt file) into deep_autoviml and it will split it into Train and Validation  datasets inside. You only need to provide a target variable, a project_name to store files in your local machine and leave the rest to defaults:

```
model, cat_vocab_dict = deepauto.run(train, target, keras_model_type="auto",
            project_name="deep_autoviml", keras_options={}, model_options={}, 
            save_model_flag=True, use_my_model='', verbose=0)
```

Once deep_autoviml writes your saved model and cat_vocab_dict files to disk in the project_name directory, you can load it from anywhere (including cloud) for predictions like this using the model and cat_vocab_dict generated above:

```
predictions = deepauto.predict_model(model, project_name, test_dataset=test,
            keras_model_type=keras_model_type, cat_vocab_dict=cat_vocab_dict)
```

## API
**Arguments**

deep_autoviml requires only a single line of code to get started. You can however, fine tune the model we build using multiple options using dictionaries named "model_options" and "keras_options". These two dictionaries act like **kwargs to enable you to fine tune hyperparameters for building our tf.keras model. Instructions on how to use them are provided below.

- `train`: could be a datapath+filename or a pandas dataframe. Deep Auto_ViML even handles gz or gzip files. You must specify the full path and file name for it find and load it.
- `target`: name of the target variable in the data set.
- `keras_model_type`: could be "auto" or any of the built-in model types such as "deep","big deep","giant deep",'cnn1','cnn2', etc. It is best to leave it at default "auto" mode.
- `project_name`: must be a string. Name of the folder where we will save your keras saved model and logs for tensorboard
- `model_options`: must be a dictionary. For example: {'max_trials':5} sets the number of trials to run Storm-Tuner to search for the best hyper parameters for your keras model.
- `keras_options`: must be a dictionary. You can use it for changing any keras model option you want such as "epochs", "kernel_initializer", "activation", "loss", "metrics", etc.
- `save_model_flag`: must be True or False. The model will be saved in keras model format.
- `use_my_model`: bring your own mode that you have defined previously. This model must be a keras Sequential model with NO input layers or output layers! We will add those layers. Just specify your hidden layers (Dense, Conv1D, Conv2D, etc.), dropouts, activations, etc. If you don't want to use this option, just leave it as "empty string".
- `verbose`: must be 0, 1 or 2. Can also be True or False.

![how_deep](deep_3.jpg)

## Tips
You can use the following arguments in your input to make deep_autoviml work best for you:
- `model_options = {"model_use_case":'pipeline'}`: If you only want keras preprocessing layers (i.e. keras pipeline) then set the model_use_case input to "pipeline" and Deep Auto_ViML will not build a model but just return the keras input and preprocessing layers. You can use these inputs and output layers to any sequential model you choose and build your own custom model.
- `model_options = {max_trials:5}`: Always start with a small number of max_trials in model_options dictionary or a dataframe. Start with 5 trials and increase it by 20 each time to see if performance improves. Stop when performance of the model doesn't improve any more. This takes time.
- `model_options = {'cat_feat_cross_flag':True}`: default is False but change it to True and see if adding feature crosses with your categorical features helps improve the model. However, this will explode the number of features in your model. Be careful.
- `model_options = {'nlp_char_limit':20}`: If you want to run NLP Text preprocessing on any column, set this character limit low and deep_autoviml will then detect that column as an NLP column automatically. The default is 30 chars.
- `keras_options = {"patience":30}`: If you want to reduce Early Stopping, then increase the patience to 30 or higher. Your model will train longer but you might get better performance.
- `use_my_model = sequential_model`: If you want to bring your own custom model for training, then define a Keras Sequential model but don't include inputs or output layers. Just define your hidden layers. Deep Auto_ViML will automatically add inputs and outputs and train your model. It will also save the model after training. You can use this model for predictions.


## Maintainers

* [@AutoViML](https://github.com/AutoViML)

## Contributing

See [the contributing file](CONTRIBUTING.md)!

PRs accepted.

## License

Apache License 2.0 © 2020 Ram Seshadri

## DISCLAIMER
This project is not an official Google project. It is not supported by Google and Google specifically disclaims all warranties as to its quality, merchantability, or fitness for a particular purpose.