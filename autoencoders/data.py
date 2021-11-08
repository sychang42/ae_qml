# Handling data input for the auto-encoder to train/test on or produce latent
# space of.
import torch
import torch.nn as nn

import numpy as np
import os, warnings, time

from .terminal_colors import tcols


class AE_data():
    def __init__(self, data_folder, norm_name, nevents,
        train_events=-1, valid_events=-1, test_events=-1):

        self.norm_name    = norm_name
        self.nevents      = nevents
        self.data_folder  = data_folder

        self.train_data   = self.get_numpy_data("train")
        self.valid_data   = self.get_numpy_data("valid")
        self.test_data    = self.get_numpy_data("test")

        self.train_target = self.get_numpy_target("train")
        self.valid_target = self.get_numpy_target("valid")
        self.test_target  = self.get_numpy_target("test")

        if int(train_events) > 0:
            self.train_data, self.train_target = \
            self.get_dataset(self.train_data, self.train_target, train_events)
        if int(valid_events) > 0:
            self.valid_data, self.valid_target = \
            self.get_dataset(self.valid_data, self.valid_target, valid_events)
        if int(test_events) > 0:
            self.test_data, self.test_target = \
            self.get_dataset(self.test_data, self.test_target, test_events)

        self.nfeats = self.train_data.shape[1]

        self.success_message()

    def get_data_file(self, data_type):
        """
        Return the string with the name of the numpy data file to be imported.
        @data_type :: String with the type of data to be imported, either
                      train, test, or valid.
        """
        return "x_data_" + self.norm_name + "_" + self.nevents + "_" + \
            data_type + ".npy"

    def get_target_file(self, data_type):
        """
        Return the string with the name of the numpy target file to be imported.
        @data_type :: String with the type of data to be imported, either
                      train, test, or valid.
        """
        return "y_data_" + self.norm_name + "_" + self.nevents + "_" + \
            data_type + ".npy"

    def get_numpy_data(self, data_type):
        """
        Load the numpy data given the type of data you want to load.
        @data_type :: String with the type of data to be imported, either
                      train, test, or valid.
        """
        data = []
        path = os.path.join(self.data_folder, self.get_data_file(data_type))
        try: data = np.load(path)
        except: print(tcols.WARNING + data_type + " data file not found!" +
                      tcols.ENDC)

        return data

    def get_numpy_target(self, data_type):
        """
        Load the numpy target given the type of data you want to load.
        @data_type :: String with the type of data to be imported, either
                      train, test, or valid.
        """
        data = []
        path = os.path.join(self.data_folder, self.get_target_file(data_type))
        try: data = np.load(path)
        except: print(tcols.WARNING + data_type + " data file not found!" +
                      tcols.ENDC)

        return data

    def get_pytorch_dataset(self, data_type):
        """
        Transform a numpy loaded data set into a pytorch data set.
        @data_type :: String with the type of data to be transformed, either
                      train, test, or valid.
        """
        switcher = {
            'train': lambda: self.make_set(self.train_data, self.train_target),
            'valid': lambda: self.make_set(self.valid_data, self.valid_target),
            'test':  lambda: self.make_set(self.test_data,  self.test_target)
        }
        dataset = switcher.get(data_type, lambda: None)()
        if dataset is None:
            raise TypeError("Dataset must be train, valid, or test!!")

        return dataset

    @staticmethod
    def make_set(data, target):
        # Make a pytorch data set from the data and target numpy arrays.
        data    = torch.Tensor(data)
        target  = torch.Tensor(target)
        return torch.utils.data.TensorDataset(data, target)

    def success_message(self):
        # Display success message for loading data when called.
        print("\n----------------")
        print(tcols.OKGREEN + "AE data loading complete:" + tcols.ENDC)
        print(f"Training data size: {self.train_data.shape[0]:.2e}")
        print(f"Validation data size: {self.valid_data.shape[0]:.2e}")
        print(f"Test data size: {self.test_data.shape[0]:.2e}")
        print("----------------\n")

    def get_loader(self, data_type, device, batch_size=None, shuffle=True):
        """
        Convert numpy arrays of training/validation/testing data into pytroch
        objects ready to be used in training the autoencoder.
        @data_type  :: String with the type of data to be transformed, either
                       train, test, or valid.
        @device     :: String if the training is done on cpu or gpu.
        @batch_size :: Int of the batch size used in training.
        @shuffle    :: Bool of whether to shuffle the data or not.

        @returns :: Pytorch objects to be passed to the autoencoder for
            training.
        """
        dataset = self.get_pytorch_dataset(data_type)
        if batch_size is None: batch_size = len(dataset)

        if device == 'cpu':
            pytorch_loader = torch.utils.data.DataLoader(dataset,
                batch_size=batch_size, shuffle=shuffle)
        else:
            pytorch_loader = torch.utils.data.DataLoader(dataset,
                batch_size=batch_size, shuffle=shuffle, pin_memory=True)

        return pytorch_loader

    @staticmethod
    def split_sig_bkg(data, target):
        """
        Split dataset into signal and background samples using the target.
        The target is supposed to be 1 for every signal and 0 for every bkg.
        @data   :: Numpy array containing the data.
        @target :: Numpy array containing the target.

        @returns :: A numpy array containing the signal events and a numpy
            array containing the background events.
        """
        sig_mask = (target == 1); bkg_mask = (target == 0)
        data_sig = data[sig_mask, :]
        data_bkg = data[bkg_mask, :]

        return data_sig, data_bkg

    def get_dataset(self, data, target, nevents):
        """
        Cut the imported data and target and form new data sets with
        equal numbers of signal and background events.

        @data    :: Numpy array containing the data.
        @target  :: Numpy array containing the target.
        @nevents :: The number of signal events the data sets should contain,
                    the number of background events will be the same.

        @returns :: Two numpy arrays, one with data and one with target,
            containing an equal number of singal and background events.
        """
        nevents = int(int(nevents)/2)
        if nevents < 0: return data, target

        data_sig, data_bkg = self.split_sig_bkg(data, target)
        data   = np.vstack((data_sig[:nevents, :], data_bkg[:nevents, :]))
        target = np.concatenate((np.ones(nevents), np.zeros(nevents)))

        return data, target
