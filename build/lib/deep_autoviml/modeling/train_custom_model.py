############################################################################################
#Copyright 2021 Google LLC

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
############################################################################################
import pandas as pd
import numpy as np
pd.set_option('display.max_columns',500)
import matplotlib.pyplot as plt
import tempfile
import pdb
import copy
import warnings
warnings.filterwarnings(action='ignore')
import functools
# Make numpy values easier to read.
np.set_printoptions(precision=3, suppress=True)
############################################################################################
# TensorFlow ≥2.4 is required
import tensorflow as tf
import os
def set_seed(seed=31415):
    np.random.seed(seed)
    tf.random.set_seed(seed)
    os.environ['PYTHONHASHSEED'] = str(seed)
    os.environ['TF_DETERMINISTIC_OPS'] = '1'
from tensorflow.keras import layers
from tensorflow import keras
from tensorflow.keras.layers.experimental.preprocessing import Normalization, StringLookup, CategoryCrossing
from tensorflow.keras.layers.experimental.preprocessing import IntegerLookup, CategoryEncoding
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization, Discretization, Hashing
from tensorflow.keras.layers import Embedding, Reshape, Dropout, Dense

from tensorflow.keras.optimizers import SGD, Adam, RMSprop
from tensorflow.keras import layers
from tensorflow.keras import optimizers
from tensorflow.keras.models import Model, load_model
from tensorflow.keras import callbacks
from tensorflow.keras import backend as K
from tensorflow.keras import utils
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.optimizers import SGD
from tensorflow.keras import regularizers
#####################################################################################
# Utils
from deep_autoviml.utilities.utilities import print_one_row_from_tf_dataset, print_one_row_from_tf_label
from deep_autoviml.utilities.utilities import print_classification_metrics, print_regression_model_stats
from deep_autoviml.utilities.utilities import print_classification_model_stats, plot_history, plot_classification_results

from deep_autoviml.data_load.extract import find_batch_size
from deep_autoviml.modeling.create_model import check_keras_options
#from deep_autoviml.modeling.one_cycle import OneCycleScheduler
#####################################################################################
from sklearn.metrics import roc_auc_score, mean_squared_error, mean_absolute_error
from IPython.core.display import Image, display
import pickle
#############################################################################################
##### Suppress all TF2 and TF1.x warnings ###################
try:
    tf.logging.set_verbosity(tf.logging.ERROR)
except:
    tf.compat.v1.logging.set_verbosity(tf.compat.v1.logging.ERROR)
############################################################################################
from tensorflow.keras.layers import Reshape, MaxPooling1D, MaxPooling2D, AveragePooling2D, AveragePooling1D
from tensorflow.keras import Model, Sequential
from tensorflow.keras.layers import Activation, Dense, Embedding, GlobalAveragePooling1D, GlobalMaxPooling1D, Dropout, Conv1D
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization
############################################################################################
#### probably the most handy function of all!
def left_subtract(l1,l2):
    lst = []
    for i in l1:
        if i not in l2:
            lst.append(i)
    return lst
##############################################################################################
import time
import os
from sklearn.metrics import balanced_accuracy_score, classification_report
from sklearn.metrics import confusion_matrix, roc_auc_score, accuracy_score
from collections import defaultdict
from tensorflow.keras import callbacks
#########################################################################################
### This is the Storm-Tuner which stands for Stochastic Random Mutator tuner
###  More details can be found in this github: https://github.com/ben-arnao/stochasticmutatortuner
###   You can also pip install storm-tuner --upgrade to get the latest version ##########
from storm_tuner import Tuner
#########################################################################################
set_seed()
class OneCycleScheduler(keras.callbacks.Callback):
    def __init__(self, iterations, max_rate, start_rate=None,
                 last_iterations=None, last_rate=None):
        self.iterations = iterations
        self.max_rate = max_rate
        self.start_rate = start_rate or max_rate / 10
        self.last_iterations = last_iterations or iterations // 10 + 1
        self.half_iteration = (iterations - self.last_iterations) // 2
        self.last_rate = last_rate or self.start_rate / 1000
        self.iteration = 0
    def _interpolate(self, iter1, iter2, rate1, rate2):
        return ((rate2 - rate1) * (self.iteration - iter1)
                / (iter2 - iter1) + rate1)
    def on_batch_begin(self, batch, logs):
        if self.iteration < self.half_iteration:
            rate = self._interpolate(0, self.half_iteration, self.start_rate, self.max_rate)
        elif self.iteration < 2 * self.half_iteration:
            rate = self._interpolate(self.half_iteration, 2 * self.half_iteration,
                                     self.max_rate, self.start_rate)
        else:
            rate = self._interpolate(2 * self.half_iteration, self.iterations,
                                     self.start_rate, self.last_rate)
        self.iteration += 1
        K.set_value(self.model.optimizer.lr, rate)
#########################################################################################
import os
def get_callbacks(val_mode, val_monitor, patience, learning_rate, save_weights_only):
    logdir = "deep_autoviml"
    tensorboard_logpath = os.path.join(logdir,"mylogs")
    #print('    Tensorboard log directory can be found at: %s' %tensorboard_logpath)
    cp = keras.callbacks.ModelCheckpoint("deep_autoviml", save_best_only=True,
                                         save_weights_only=save_weights_only, save_format='tf')
    ### sometimes a model falters and restore_best_weights gives len() not found error. So avoid True option!
    lr_patience = max(2,int(patience*0.5))
    rlr = callbacks.ReduceLROnPlateau(monitor=val_monitor, factor=0.75,
                    patience=lr_patience, min_lr=1e-6, mode='auto', min_delta=0.00001, cooldown=0, verbose=1)

    steps = 10
    onecycle = OneCycleScheduler(iterations=steps, max_rate=0.05)

    lr_sched = callbacks.LearningRateScheduler(lambda epoch: 1e-4 * (0.75 ** np.floor(epoch / 2)))

      # Setup Learning Rate decay.
    lr_decay_cb = callbacks.LearningRateScheduler(
        lambda epoch: learning_rate - 0.02 * (0.5 ** (1 + epoch)),
        verbose=False)

    es = callbacks.EarlyStopping(monitor=val_monitor, min_delta=0.00001, patience=patience,
                        verbose=1, mode=val_mode, baseline=None, restore_best_weights=True)
    
    tb = callbacks.TensorBoard(tensorboard_logpath)
    
    callbacks_list = [cp, lr_sched, es, tb]

    return callbacks_list, tensorboard_logpath
####################################################################################
### Split raw_train_set into train and valid data sets first
### This is a better way to split a dataset into train and test ####
### It does not assume a pre-defined size for the data set.
def is_valid(x, y):
    return x % 5 == 0
def is_test(x, y):
    return x % 2 == 0
def is_train(x, y):
    return not is_test(x, y)
##################################################################################
def get_uncompiled_model(inputs, result, model_body, output_activation, 
                    num_predicts, num_labels, cols_len):
    ### The next 3 steps are most important! Don't mess with them! 
    #model_preprocessing = Model(inputs, meta_outputs)
    #preprocessed_inputs = model_preprocessing(inputs)
    #result = model_body(preprocessed_inputs)
    ##### now you
    multi_label_predictions = defaultdict(list)
    for each_label in range(num_labels):
        key = 'predictions'        
        value = layers.Dense(num_predicts, activation=output_activation,
                            name='output_'+str(each_label))(result)
        multi_label_predictions[key].append(value)
    outputs = multi_label_predictions[key] ### outputs will be a list of Dense layers

    ##### Set the inputs and outputs of the model here
    uncompiled_model = Model(inputs=inputs, outputs=outputs)
    return uncompiled_model

def get_compiled_model(inputs, meta_outputs, output_activation, num_predicts, num_labels, 
                      model_body, optimizer, val_loss, val_metrics, cols_len):
    model = get_uncompiled_model(inputs, meta_outputs, model_body, output_activation, 
                        num_predicts, num_labels, cols_len)
    model.compile(
        optimizer=optimizer,
        loss=val_loss,
        metrics=val_metrics,
    )
    return model
###############################################################################
def build_model(hp):
    model_body = Sequential()

    # example of model-wide unordered categorical parameter
    activation_fn = hp.Param('activation', ['tanh','relu', 'selu', 'elu'])

    # example of per-block parameter
    model_body.add(Dense(hp.Param('kernel_size_' + str(0), 
                             sorted(np.linspace(64,400,100).astype(int),reverse=True), 
                             ordered=True), use_bias=False,
                         kernel_initializer = hp.Param('kernel_initializer',
                      ['glorot_uniform','he_normal','lecun_normal','he_uniform'],ordered=False),
                         name="dense_0",
                             kernel_regularizer=keras.regularizers.l2(0.01)))

    model_body.add(Activation(activation_fn,name="activation_0"))

    # example of boolean param
    if hp.Param('use_batch_norm', [True, False]):
        model_body.add(BatchNormalization(name="batch_norm_0"))

    if hp.Param('use_dropout', [True, False]):

        # example of nested param
        #
        # this param will not affect the configuration hash, if this block of code isn't executed
        # this is to ensure we do not test configurations that are functionally the same
        # but have different values for unused parameters
        model_body.add(Dropout(hp.Param('dropout_value', [0.1, 0.2, 0.3, 0.4, 0.5], ordered=True),
                                        name="dropout_0"))
    kernel_size =  hp.values['kernel_size_' + str(0)]
    dropout_flag = hp.values['use_dropout']
    if dropout_flag:
        dropout_value = hp.values['dropout_value']
    else:
        dropout_value =  0.05
    batch_norm_flag = hp.values['use_batch_norm']
    # example of inline ordered parameter
    for x in range(hp.Param('num_layers', [1, 2, 3, 4, 5, 6], ordered=True)):

        kernel_size = int(0.75*kernel_size)
        # example of per-block parameter
        model_body.add(Dense(kernel_size, name="dense_"+str(x+1), use_bias=False,
                         kernel_initializer = hp.Param('kernel_initializer',
                      ['glorot_uniform','he_normal','lecun_normal','he_uniform'],ordered=False),
                             kernel_regularizer=keras.regularizers.l2(0.01)))
        
        model_body.add(Activation(activation_fn, name="activation_"+str(x+10)))

        # example of boolean param
        if batch_norm_flag:
            model_body.add(BatchNormalization(name="batch_norm_"+str(x+1)))

        if dropout_flag:
            # example of nested param
            # this param will not affect the configuration hash, if this block of code isn't executed
            # this is to ensure we do not test configurations that are functionally the same
            # but have different values for unused parameters
            model_body.add(Dropout(dropout_value, name="dropout_"+str(x+1)))

    return model_body
############################################################################################
class MyTuner(Tuner):

    def run_trial(self, trial, *args):
        hp = trial.hyperparameters
        model_body = build_model(hp)
        train_ds, valid_ds = args[0], args[1]
        epochs, steps =  args[2], args[3]
        inputs, meta_outputs = args[4], args[5]
        cols_len, output_activation = args[6], args[7]
        num_predicts, num_labels = args[8], args[9]
        optimizer, val_loss =  args[10], args[11]
        val_metrics, patience = args[12], args[13]
        val_mode, DS_LEN = args[14], args[15]
        learning_rate, val_monitor = args[16], args[17]


        ##  now load the model_body and convert it to functional model
        #print('Loading custom model...')
        ##### This is the simplest way to convert a sequential model to functional!
        for num, each_layer in enumerate(model_body.layers):
            if num == 0:
                final_outputs = each_layer(meta_outputs)
            else:
                final_outputs = each_layer(final_outputs)
        #### This final outputs is the one that is taken into final dense layer and compiled
        #print('    Custom model loaded successfully. Now compiling model...')

        ###### This is where you compile the model after it is built ###############
        #### Add a final layer for outputs during compiled model phase #############
        np.random.seed(42)
        selected_optimizer = hp.Param('optimizer', ["Adam","AdaMax","Adagrad","SGD",
                                "RMSprop","Nadam",'nesterov'],
                            ordered=False)
        optimizer = return_optimizer(hp, selected_optimizer, trial_flag=True)
        
        comp_model = get_compiled_model(inputs, final_outputs, output_activation, num_predicts, 
                            num_labels, model_body, optimizer, val_loss, val_metrics, cols_len)

        # here we can access params generated in the builder function
        # example of supplementary paramteter that will be accessed elsewhere  ##
        batch_limit = int(2*find_batch_size(DS_LEN))
        batch_nums = int(max(10, 0.1*batch_limit))
        batch_size = hp.Param('batch_size', sorted(np.linspace(32,
                            batch_limit,batch_nums).astype(int),reverse=True),
                            ordered=True)
        #print('    Custom model compiled successfully. Training model next...')
        shuffle_size = 1000000
        #batch_size = hp.Param('batch_size', [64, 128, 256], ordered=True)
        train_ds = train_ds.unbatch().batch(batch_size)
        train_ds = train_ds.shuffle(shuffle_size, 
                        reshuffle_each_iteration=False, seed=42).prefetch(batch_size).repeat(5)
        valid_ds = valid_ds.unbatch().batch(batch_size)
        valid_ds = valid_ds.prefetch(batch_size).repeat(5)
        steps = 20
        #scores = []
        lr_patience = max(2,int(patience*0.5))
        rlr = callbacks.ReduceLROnPlateau(monitor=val_monitor, factor=0.95,
                    patience=lr_patience, min_lr=1e-6, mode='auto', min_delta=0.001, cooldown=0, verbose=1)
        es = callbacks.EarlyStopping(monitor=val_monitor, min_delta=0.00001, patience=patience,
                        verbose=0, mode=val_mode, baseline=None, restore_best_weights=True)

        history = comp_model.fit(train_ds, epochs=epochs, steps_per_epoch=steps,# batch_size=batch_size, 
                            validation_data=valid_ds, validation_steps=steps,
                            callbacks=[rlr, es], shuffle=False,
                            verbose=0)
        # here we can define custom logic to assign a score to a configuration
        if num_labels == 1:
            score = np.mean(history.history[val_monitor][-5:])
        else:
            for i in range(num_labels):
                val_metric = val_monitor.split("_")[-1]
                val_metric = 'val_output_'+str(i)+'_' + val_metric
                if i == 0:
                    results = history.history[val_metric][-5:]
                else:
                    results = np.c_[results,history.history[val_metric][-5:]]
            score = results.mean(axis=1).mean()
            #scores.append(score)
        ##### This is where we capture the best learning rate from the optimizer chosen ######
        model_lr = comp_model.optimizer.learning_rate.numpy()
        self.user_var = model_lr
        #print('    model lr = %s' %model_lr)
        trial.metrics['final_lr'] = history.history['lr'][-1]
        #print('    trial lr = %s' %trial.metrics['final_lr'])
        self.score_trial(trial, score) 
        #self.score_trial(trial, min(scores)) 
#####################################################################################
def return_optimizer(hp, hpq_optimizer, trial_flag=False):
    """
    This returns the keras optimizer with proper inputs if you send the string.
    hpq_optimizer: input string that stands for an optimizer such as "Adam", etc.
    """
    ##### These are the various optimizers we use ################################
    momentum = keras.optimizers.SGD(lr=0.001, momentum=0.9)
    nesterov = keras.optimizers.SGD(lr=0.001, momentum=0.9, nesterov=True)
    adagrad = keras.optimizers.Adagrad(lr=0.001)
    rmsprop = keras.optimizers.RMSprop(lr=0.001, rho=0.9)
    adam = keras.optimizers.Adam(lr=0.001, beta_1=0.9, beta_2=0.999)
    adamax = keras.optimizers.Adamax(lr=0.001, beta_1=0.9, beta_2=0.999)
    nadam = keras.optimizers.Nadam(lr=0.001, beta_1=0.9, beta_2=0.999)
    #############################################################################
    if trial_flag:
        if hpq_optimizer == 'Adam':
            best_optimizer = tf.keras.optimizers.Adam(lr=hp.Param('init_lr', [1e-2, 1e-3, 1e-4]),
                epsilon=hp.Param('epsilon', [1e-6, 1e-8, 1e-10, 1e-12, 1e-14], ordered=True))
        elif hpq_optimizer == 'SGD':
            best_optimizer = keras.optimizers.SGD(lr=hp.Param('init_lr', [1e-2, 1e-3, 1e-4]),
                                 momentum=0.9)
        elif hpq_optimizer == 'Nadam':
            best_optimizer = keras.optimizers.Nadam(lr=hp.Param('init_lr', [1e-2, 1e-3, 1e-4]),
                             beta_1=0.9, beta_2=0.999)
        elif hpq_optimizer == 'AdaMax':
            best_optimizer = keras.optimizers.Adamax(lr=hp.Param('init_lr', [1e-2, 1e-3, 1e-4]),
                             beta_1=0.9, beta_2=0.999)
        elif hpq_optimizer == 'Adagrad':
            best_optimizer = keras.optimizers.Adagrad(lr=hp.Param('init_lr', [1e-2, 1e-3, 1e-4]))
        elif hpq_optimizer == 'RMSprop':
            best_optimizer = keras.optimizers.RMSprop(lr=hp.Param('init_lr', [1e-2, 1e-3, 1e-4]),
                             rho=0.9)
        else:
            best_optimizer = keras.optimizers.SGD(lr=0.001, momentum=0.9, nesterov=True)
    else:
        #### This could be turned into a dictionary but for now leave is as is for readability ##
        if hpq_optimizer == 'Adam':
            best_optimizer = adam
        elif hpq_optimizer == 'SGD':
            best_optimizer = momentum
        elif hpq_optimizer == 'Nadam':
            best_optimizer = nadam
        elif hpq_optimizer == 'AdaMax':
            best_optimizer = adamax
        elif hpq_optimizer == 'Adagrad':
            best_optimizer = adagrad
        elif hpq_optimizer == 'RMSprop':
            best_optimizer = rmsprop
        else:
            best_optimizer = nesterov
    return best_optimizer
##########################################################################################
def train_custom_model(inputs, meta_outputs, full_ds, target, keras_model_type, 
                    keras_options, model_options, var_df, cat_vocab_dict, project_name="", 
                    save_model_flag=True, use_my_model='', verbose=0 ):
    """
    Given a keras model and a tf.data.dataset that is batched, this function will 
    train a keras model. It will first split the batched_data into train_ds and  
    valid_ds (80/20). Then it will select the right parameters based on model type and 
    train the model and evaluate it on valid_ds. It will return a keras model fully 
    trained on the full batched_data finally and train history.
    """
    ########################   STORM TUNER and other DEFAULTS     ####################
    max_trials = model_options["max_trials"]
    overwrite_flag = True ### This overwrites the trials so every time it runs it is new
    data_size = check_keras_options(keras_options, 'data_size', 10000)
    batch_size = check_keras_options(keras_options, 'batchsize', 64)
    num_classes = model_options["num_classes"]
    num_labels = model_options["num_labels"]
    modeltype = model_options["modeltype"]
    patience = check_keras_options(keras_options, "patience", 10)
    cols_len = len([item for sublist in list(var_df.values()) for item in sublist])
    data_dim = int(data_size*meta_outputs.shape[1])
    print('After preprocessing using keras layers, features dimensions is now %s' %meta_outputs.shape[1])
    print('    original datasize = %s, initial batchsize = %s' %(data_size, batch_size))
    NUMBER_OF_EPOCHS = check_keras_options(keras_options, "epochs", 100)
    learning_rate = 5e-1
    steps = max(10, data_size//(batch_size*5))
    print('    recommended steps per epoch = %d' %steps)
    STEPS_PER_EPOCH = check_keras_options(keras_options, "steps_per_epoch", 
                        steps)
    #keras.optimizers.schedules.ExponentialDecay(0.01,STEPS_PER_EPOCH, 0.95)
    #### These can be standard for every keras option that you use layers ######
    kernel_initializer = check_keras_options(keras_options, 'kernel_initializer', 'lecun_normal')
    activation='selu'
    print('    default initializer = %s, default activation = %s' %(kernel_initializer, activation))
    #####   set some defaults for model parameters here ##
    optimizer = check_keras_options(keras_options,'optimizer', Adam(lr=learning_rate, beta_1=0.9, beta_2=0.999))
    #optimizer = SGD(lr=learning_rate, momentum = 0.9)
    print('    Using optimizer = %s' %str(optimizer).split(".")[-1][:8])
    use_bias = check_keras_options(keras_options, 'use_bias', True)
    #######################################################################
    val_mode = keras_options["mode"]
    val_monitor = keras_options["monitor"]
    val_loss = keras_options["loss"]
    val_metrics = keras_options["metrics"]
    if modeltype == 'Regression':
        num_predicts = 1*num_labels
        output_activation = "linear"
    elif modeltype == 'Classification':
        num_predicts = int(num_classes*num_labels)
        output_activation = "sigmoid"
    else:
        num_predicts = int(num_classes*num_labels)
        output_activation = "sigmoid"
    ########################################################################
    print('    loss fn = %s\n    num predicts = %s, output_activation = %s' %(
                        val_loss, num_predicts, output_activation))
    ####  just use modeltype for printing that's all ###
    modeltype = cat_vocab_dict['modeltype']
    start_time = time.time()
    ### check the defaults for the following!
    save_weights_only = check_keras_options(keras_options, "save_weights_only", False)

    if STEPS_PER_EPOCH > NUMBER_OF_EPOCHS:
        STEPS_PER_EPOCH = max(2, int(NUMBER_OF_EPOCHS/25))
    print('    steps_per_epoch = %s, number epochs = %s' %(STEPS_PER_EPOCH, NUMBER_OF_EPOCHS))
    patience = check_keras_options(keras_options,"patience", 10)
    print('    val mode = %s, val monitor = %s, patience = %s' %(val_mode, val_monitor, patience))

    callbacks_list, tb_logpath = get_callbacks(val_mode, val_monitor, patience,
                                               learning_rate, save_weights_only)

    ###### You can use Storm Tuner to set the batch size ############
    ############## Split train into train and validation datasets here ###############
    recover = lambda x,y: y
    print('\nSplitting train into two: train and validation data')
    valid_ds1 = full_ds.enumerate().filter(is_valid).map(recover)
    train_ds = full_ds.enumerate().filter(is_train).map(recover)
    heldout_ds1 = valid_ds1
    ##################################################################################
    valid_ds = heldout_ds1.enumerate().filter(is_test).map(recover)
    heldout_ds = heldout_ds1.enumerate().filter(is_test).map(recover)
    print('    Splitting validation into two: valid and heldout data')
    ##################################################################################
    ###   V E R Y    I M P O R T A N T  S T E P   B E F O R E   M O D E L   F I T  ###    
    ##################################################################################
    shuffle_size = 100000
    y_test = np.concatenate(list(heldout_ds.map(lambda x,y: y).as_numpy_iterator()))
    if modeltype == 'Regression':
        if (y_test>=0).all() :
            ### if there are no negative values, then set output as positives only
            output_activation = 'softplus'
            print('Setting output activation layer as softplus since there are no negative values')            
    #print(' Shuffle size = %d' %shuffle_size)
    #train_ds = train_ds.prefetch(batch_size).shuffle(shuffle_size, 
    #                        reshuffle_each_iteration=False, seed=42).repeat()
    #valid_ds = valid_ds.prefetch(batch_size).repeat()
    print('Training %s model now. This will take time...' %keras_model_type)
    if isinstance(use_my_model, str):
        trials_saved_path = os.path.join(project_name,keras_model_type)
        if not os.path.exists(trials_saved_path):
            os.makedirs(trials_saved_path)
        ########   S T O R M   T U N E R   D E F I N E D     H E R E ########### 
        randomization_factor = 0.50
        tuner = MyTuner(project_dir=trials_saved_path,
                    build_fn=build_model,
                    objective_direction=val_mode,
                    init_random=5,
                    max_iters=max_trials,
                    randomize_axis_factor=randomization_factor,
                    overwrite=True)
        ###################   S T o R M   T U N E R   ###############################
        # parameters passed through 'search' go directly to the 'run_trial' method ##
        #### This is where you find best model parameters for keras using SToRM #####
        #############################################################################
        start_time1 = time.time()
        print('    STORM Tuner max_trials = %d, randomization factor = %0.1f' %(
                            max_trials, randomization_factor))
        tuner_epochs = 100  ### keep this low so you can run fast
        tuner_steps = steps  ## keep this also very low 
        #### You have to make sure that inputs are unique, otherwise error ####
        tuner.search(train_ds, valid_ds, tuner_epochs, tuner_steps, 
                            inputs, meta_outputs, cols_len, output_activation,
                            num_predicts, num_labels, optimizer, val_loss,
                            val_metrics, patience, val_mode, data_size,
                            learning_rate, val_monitor,
                            )
        #K.clear_session()
        best_trial = tuner.get_best_trial()
        print('    best trial selected as %s' %best_trial)
        ##### get the best model parameters now. Also split it into two models ###########
        hpq = tuner.get_best_config()
        try:
            best_model = build_model(hpq)
            deep_model = build_model(hpq)
        except:
            ### Sometimes the tuner cannot find a config that works!
            deep_model = return_model_body(keras_options)
            best_model = return_model_body(keras_options)
            
        if cols_len <= 100:
            try:
                tf.keras.utils.plot_model(model = best_model , rankdir="LR", dpi=72, show_shapes=True)
            except:
                print('Could not plot model since pydot and graphviz may not be in this device')
                      
        print('Time taken for tuning hyperparameters = %0.0f (mins)' %((time.time()-start_time1)/60))
        ##########    S E L E C T   B E S T   O P T I M I Z E R and L R  H E R E ############
        try:
            #optimizer_lr = tuner.model_lr
            optimizer_lr = best_trial.metrics['final_lr']
        except:
            optimizer_lr = 0.01
            print('    trial lr erroring. Seting default LR as %s' %optimizer_lr)
        try:
            best_batch = hpq.values['batch_size']
            hpq_optimizer = hpq.values['optimizer']
            best_optimizer = return_optimizer(hpq, hpq_optimizer, trial_flag=False)
        except:
            ### In some cases, the tuner doesn't select a good config in that case ##
            best_batch = batch_size
            hpq_optimizer = 'SGD'
            best_optimizer = keras.optimizers.SGD(lr=0.001, momentum=0.9, nesterov=True)
        ### Set the learning rate for the best optimizer here ######
        if optimizer_lr < 0:
            print('    best learning rate less than zero. Resetting it....')
            optimizer_lr = 0.01
        print('\nBest optimizer = %s and best learning_rate = %s' %(hpq_optimizer, optimizer_lr))
        K.set_value(best_optimizer.learning_rate, optimizer_lr)
        #######################################################################################
        print('Best hyperparameters: %s' %hpq.values)
    else:
        print('skipping tuner search since use_my_model flag set to True...')
        best_model = use_my_model
        deep_model = use_my_model
        best_optimizer = 'Adam'
        best_batch = batch_size
    ##### This is the simplest way to convert a sequential model to functional!
    for num, each_layer in enumerate(best_model.layers):
        if num == 0:
            final_outputs = each_layer(meta_outputs)
        else:
            final_outputs = each_layer(final_outputs)
    #######################################################################################
    #### The best_model will be used for predictions on valid_ds to get metrics #########
    best_model = get_compiled_model(inputs, final_outputs, output_activation, num_predicts, 
                        num_labels, best_model, best_optimizer, val_loss, val_metrics, cols_len)
    #######################################################################################
    #### here we can define the custom logic to assign a score to the model to monitor
    if num_labels > 1:
        ### You must choose one of the label outputs to monitor - we will choose the last one
        val_monitor = val_monitor.split("_")[-1]
        val_monitor = 'val_output_'+str(num_labels-1)+'_' + val_monitor

    ####################################################################################
    #####    LEARNING RATE CHEDULING : Setup Learning Rate Multiple Ways #########
    ####################################################################################
    #### Onecycle is another fast way to find the best learning in large datasets ######
    onecycle = OneCycleScheduler(iterations=steps, max_rate=0.05)
    ####  This lr_sched is a fast way to reduce LR but it can easily overfit quickly #####
    lr_sched = callbacks.LearningRateScheduler(lambda epoch: 1e-1 * (0.75 ** np.floor(epoch / 2)))
    ## RLR is the easiest one to handle as it reduces learning rate when there is no improvement ##
    lr_patience = max(2,int(patience*0.5))
    rlr = callbacks.ReduceLROnPlateau(monitor=val_monitor, factor=0.95,
                    patience=lr_patience, min_lr=1e-6, mode='auto', min_delta=0.001, cooldown=0, verbose=1)
    #### lr_decay originally used to give good results but not anymore #######
    lr_decay_cb = callbacks.LearningRateScheduler(
        lambda epoch: learning_rate - 0.02 * (0.5 ** (1 + epoch)),
        verbose=False)

    ##### Now you must try the best_model to choose the best learning_rate ####
    logdir = "deep_autoviml"
    tensorboard_logpath = os.path.join(logdir,"mylogs")
    tb = callbacks.TensorBoard(tensorboard_logpath)
    ###    E A R L Y    S T O P P I N G    T O    P R E V E N T   O V E R F I T T I N G  ##
    es = callbacks.EarlyStopping(monitor=val_monitor, min_delta=0.00001, patience=patience,
                        verbose=0, mode=val_mode, baseline=None, restore_best_weights=True)

    ####################################################################################
    #####   T E N S O R  B O A R D    C  A  N     B E   F O U N D    H E R E ######
    ####################################################################################
    print('\nTensorboard log directory can be found at: %s' %tensorboard_logpath)
    
    train_ds = train_ds.unbatch().batch(best_batch)
    train_ds = train_ds.shuffle(shuffle_size, 
                reshuffle_each_iteration=False, seed=42).prefetch(best_batch).repeat()

    valid_ds = valid_ds.unbatch().batch(best_batch)
    valid_ds = valid_ds.prefetch(best_batch).repeat()

    ####################################################################################
    ############### F I R S T  T R A I N   F O R  1 0 0   E P O C H S ##################
    ### You have to set both callbacks in order to learn what the best learning rate is 
    ####################################################################################
    np.random.seed(42)
    tf.random.set_seed(42)
    NUMBER_OF_EPOCHS = 100
    callbacks_list = [rlr, es, tb]
    print('Model training with best hyperparameters for %d epochs' %NUMBER_OF_EPOCHS)
    ####  Do this with LR scheduling but NO early stopping since we want the model fully trained #####
    history = best_model.fit(train_ds, validation_data=valid_ds,
                epochs=NUMBER_OF_EPOCHS, steps_per_epoch=STEPS_PER_EPOCH, 
                callbacks=callbacks_list, 
                validation_steps=STEPS_PER_EPOCH,
               shuffle=False)
    K.clear_session()
    
    ###   Once the best learning rate is chosen the model is ready to be trained on full data
    print('    Model training metrics available: %s' %history.history.keys())
    try:
        stopped_epoch = pd.DataFrame(history.history).shape[0] ## this is where it stopped
    except:
        stopped_epoch = 100
    ###  Plot the epochs and loss metrics here #####################
    try:
        #print('    Additionally, Tensorboard logs can be found here: %s' %tb_logpath)
        if modeltype == 'Regression':
            plot_history(history, val_monitor[4:], num_labels)
        elif modeltype == 'Classification':
            plot_history(history, val_monitor[4:], num_labels)
        else:
            plot_history(history, val_monitor[4:], num_labels)
    except:
        print('    Plot history is erroring. Tensorboard logs can be found here: %s' %tb_logpath)

    print('Time taken to train model (in mins) = %0.0f' %((time.time()-start_time)/60))
    print('    Stopped epoch = %s' %stopped_epoch)

    #################################################################################
    ########     P R E D I C T   O N   H E L D   O U T  D A T A   H E R E      ######
    #################################################################################
    scores = []
    ls = []
    print('Held out data actuals shape: %s' %(y_test.shape,))
    if verbose >= 1:
        print_one_row_from_tf_label(heldout_ds)
    ###########################################################################
    y_probas = best_model.predict(heldout_ds)
    y_test_preds_list = []
    
    if isinstance(target, str):
        if modeltype != 'Regression':
            y_test_preds = y_probas.argmax(axis=1)
        else:
            if y_test.dtype == 'int':
                y_test_preds = y_probas.round().astype(int)
            else:
                y_test_preds = y_probas.ravel()
        y_test_preds_list.append(y_test_preds)
    else:
        if modeltype != 'Regression':
            ### This is for Multi-Label Classification ###
            for each_target in target:
                #### Modify: Not sure about how this will work for multi-class, multi-output problems
                y_test_preds = y_test_preds.argmax(axis=1)
            else:
                if y_test.dtype == 'int':
                    y_test_preds = y_test_preds.round().astype(int)
                else:
                    y_test_preds = y_test_preds
            y_test_preds_list.append(y_test_preds.ravel())
        else:
            ### This is for Multi-Label Regressison ###
            for each_t in range(len(y_probas)):
                if each_t == 0:
                    y_test_preds = y_probas[each_t].mean(axis=1)
                else:
                    y_test_preds = np.c_[y_test_preds, y_probas[each_t].mean(axis=1)]
            if y_test.dtype == 'int':
                y_test_preds = y_test_preds.round().astype(int)
            y_test_preds_list.append(y_test_preds)

    print('\nHeld out predictions shape:%s' %(y_test_preds.shape,))
    if verbose >= 1:
        if modeltype != 'Regression':
            print('    Sample predictions: %s' %y_test_preds[:10])
        else:
            if num_labels == 1:
                print('    Sample predictions: %s' %y_test_preds.ravel()[:10])
            else:
                print('    Sample predictions:\n%s' %y_test_preds[:10])
    
    #################################################################################
    ########     P L O T T I N G   V A L I D A T I O N   R E S U L T S         ######
    #################################################################################
    print('\n###########################################################')
    print('         Held-out test data set Results:')
    num_labels = cat_vocab_dict['num_labels']
    num_classes = cat_vocab_dict['num_classes']
    if num_labels <= 1:
        if modeltype == 'Regression':
            print_regression_model_stats(y_test, y_test_preds,target,plot_name="deep_autoviml")
        else:
            if num_classes <= 2:
                labels = target_names = np.unique(y_test)
                plot_classification_results(y_test, y_probas, labels, target_names)
                print_classification_metrics(y_test, y_probas, proba_flag=True)
            else:
                ###### Use a nice classification matrix printing module here #########
                labels = target_names = np.unique(y_test)
                try:
                    plot_classification_results(y_test, y_probas, labels, target_names)
                except:
                    pass
                print_classification_metrics(y_test, y_probas, proba_flag=True)
                print(classification_report(y_test,y_test_preds))
                print(confusion_matrix(y_test, y_test_preds))
    else:
        if modeltype == 'Regression':
            #### This is for Multi-Label Regression ################################
            print_regression_model_stats(y_test, y_test_preds,target,plot_name="deep_autoviml")
        else:
            #### This is for Multi-Label Classification ################################
            print_classification_metrics(y_test, y_test_preds, False)
            print(classification_report(y_test, y_test_preds ))
    ### plot the regression results here #########
    if modeltype == 'Regression':
        if isinstance(target, str):
            plt.figure(figsize=(15,6))
            ax1 = plt.subplot(1, 2, 1)
            ax1.scatter(x=y_test, y=y_test_preds,)
            ax1.set_title('Actuals (x-axis) vs. Predictions (y-axis)')
            pdf = save_valid_predictions(y_test, y_test_preds.ravel(), project_name, num_labels)
            ax2 = plt.subplot(1, 2, 2)
            pdf.plot(ax=ax2)
        else:
            pdf = save_valid_predictions(y_test, y_test_preds, project_name, num_labels)
            plt.figure(figsize=(15,6))
            for i in range(num_labels):
                ax1 = plt.subplot(1, num_labels, i+1)
                ax1.scatter(x=y_test[:,i], y=y_test_preds[:,i])
                ax1.set_title(f"Actuals_{i} (x-axis) vs. Predictions_{i} (y-axis)")
            plt.figure(figsize=(15, 6)) 
            for j in range(num_labels):
                pair_cols = ['actuals_'+str(j), 'predictions_'+str(j)]
                ax2 = plt.subplot(1, num_labels, j+1)
                pdf[pair_cols].plot(ax=ax2)

    ##################################################################################
    ###   S E C O N D   T R A I N   O N  F U L L   T R A I N   D A T A   S E T     ###    
    ##################################################################################
    ############       train the model on full train data set now      ###############
    print('\nTraining full train dataset. This will take time...')
    full_ds = full_ds.unbatch().batch(best_batch)
    full_ds = full_ds.shuffle(shuffle_size, 
            reshuffle_each_iteration=False, seed=42).prefetch(best_batch).repeat()
    #################   B E S T    O P T I M I Z E R     ##########################
    ##### You need to set the best optimizer from the best_model #################
    deep_optimizer = best_model.optimizer
    ## The deep_model will be trained on full_dataset and saved as the final model ##########
    deep_model = get_compiled_model(inputs, final_outputs, output_activation, num_predicts, 
                        num_labels, deep_model, deep_optimizer, val_loss, val_metrics, cols_len)

    ##### You need to set the best learning rate from the best_model #################
    best_rate = best_model.optimizer.lr.numpy()
    if best_rate < 0:
        print('    best learning rate less than zero. Resetting it....')
        #best_rate = 0.01
    else:
        pass
        #print('    best learning rate = %s' %best_rate)
    #K.set_value(deep_model.optimizer.learning_rate, best_rate)
    #print("    set learning rate using best model:", deep_model.optimizer.learning_rate.numpy())
    ####   Dont set the epochs too low - let them be back to where they were stopped  ####
    print('    max epochs for training = %d' %stopped_epoch)
    deep_model.fit(full_ds, epochs=stopped_epoch, steps_per_epoch=STEPS_PER_EPOCH, 
                    batch_size=best_batch,
                    callbacks=[rlr],  shuffle=True, verbose=0)

    ##################################################################################
    #######        S A V E the model here using save_model_name      #################
    ##################################################################################
    
    if isinstance(project_name,str):
        if project_name == '':
            project_name = "deep_autoviml"
    else:
        print('Project name must be a string and helps create a folder to store model.')
        project_name = "deep_autoviml"
    save_model_path = os.path.join(project_name,keras_model_type)
    cat_vocab_dict['project_name'] = project_name

    if save_model_flag:
        print('\nSaving model in %s now...this will take time...' %save_model_path)
        if not os.path.exists(save_model_path):
            os.makedirs(save_model_path)
        deep_model.save(save_model_path)
        cat_vocab_dict['saved_model_path'] = save_model_path
        print('     deep model saved in %s directory' %save_model_path)
    else:
        print('\nModel not being saved since save_model_flag set to False...')

    #### make sure you save the cat_vocab_dict to use later during predictions
    try:
        pickle_path = os.path.join(project_name,"cat_vocab_dict")+".pickle"
        if not os.path.exists(project_name):
            os.makedirs(project_name)
        print('\nSaving vocab dictionary using pickle in %s...will take time...' %pickle_path)
        with open(pickle_path, "wb") as fileopen:
            fileopen.write(pickle.dumps(cat_vocab_dict))
        print('    Saved pickle file in %s' %pickle_path)
    except:
        print('Unable to save cat_vocab_dict - please pickle it yourself.')
    ####### make sure you save the variable definitions file ###########
    try:
        pickle_path = os.path.join(project_name,"var_df")+".pickle"
        if not os.path.exists(project_name):
            os.makedirs(project_name)
        print('\nSaving variable definitions file using pickle in %s...will take time...' %pickle_path)
        with open(pickle_path, "wb") as fileopen:
            fileopen.write(pickle.dumps(var_df))
        print('    Saved pickle file in %s' %pickle_path)
    except:
        print('Unable to save cat_vocab_dict - please pickle it yourself.')

    print('Deep_Auto_ViML completed. Total time = %0.0f (in mins)' %((time.time()-start_time)/60))

    return deep_model, cat_vocab_dict
######################################################################################
import os
def save_valid_predictions(y_test, y_preds, project_name, num_labels):
    if num_labels == 1:
        pdf = pd.DataFrame([y_test, y_preds])
        pdf = pdf.T
        pdf.columns= ['actuals','predictions']
    else:
        pdf = pd.DataFrame(np.c_[y_test, y_preds])
        act_names = ['actuals_'+str(x) for x in range(y_test.shape[1])]
        pred_names = ['predictions_'+str(x) for x in range(y_preds.shape[1])]
        pdf.columns = act_names + pred_names
    preds_file = project_name+'_predictions.csv'
    preds_path = os.path.join(project_name, preds_file)
    pdf.to_csv(preds_path,index=False)
    print('Saved predictions in %s file' %preds_path)
    return pdf
#########################################################################################    
def return_model_body(keras_options):
    num_layers = check_keras_options(keras_options, 'num_layers', 2)
    model_body = tf.keras.Sequential([])
    for l_ in range(num_layers):
        model_body.add(layers.Dense(64, activation='relu', kernel_initializer="lecun_normal",
                                    activity_regularizer=tf.keras.regularizers.l2(0.01)))
    return model_body
########################################################################################