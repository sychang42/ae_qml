# Utility methods for the qsvm.

import os
import joblib
from datetime import datetime

from .terminal_colors import tcols


def print_accuracies(test_accuracy, train_accuracy):
    """
    Prints the accuracies of the qsvm.
    @test_accuracy  :: Numpy array of the test data set accuracies.
    @train_accuracy :: Numpy array of the train data set accuracies.
    """
    print(tcols.OKGREEN + f"Training Accuracy = {train_accuracy}")
    print(f"Test Accuracy     = {test_accuracy}" + tcols.ENDC)


def create_output_folder(output_folder):
    """
    Creates output folder for the qsvm.
    @output_folder :: Name of the output folder for this particular
                      version of the qsvm.
    """
    if not os.path.exists("qsvm_models/" + output_folder):
        os.makedirs("qsvm_models/" + output_folder)


def save_qsvm(model, path):
    """
    Saves the qsvm model to a certain path.
    @model :: qsvm model object.
    @path  :: String of full path to save the model in.
    """
    joblib.dump(model, path)
    print("Trained model saved in: " + path)


def load_qsvm(path):
    """
    Load model from pickle file, i.e., deserialisation.
    @path  :: String of full path to save the model in.

    returns :: Joblib object that can be loaded by qiskit.
    """
    return joblib.load(path)


def print_model_info(ae_path, qdata, qsvm):

    print("\n-------------------------------------------")
    print(f"Autoencoder model: {ae_path}")
    print(f"Data path: {qdata.ae_data.data_folder}")
    print(
        f"ntrain = {len(qdata.ae_data.trtarget)}, "
        f"ntest = {len(qdata.ae_data.tetarget)}, "
        f"C = {qsvm.C}"
    )
    print("-------------------------------------------\n")


def save_model(qdata, qsvm, train_acc, test_acc, output_folder, ae_path):
    """
    Save the model and a log of useful info regarding the saved model.
    @qdata         :: The data that was processed by the qsvm.
    @qsvm          :: The qiskit qsvm object.
    @train_acc     :: Numpy array of the training accuracies.
    @test_acc      :: Numpy array of the testing accuracies.
    @output_folder :: String of the output folder where the saving is.
    @ae_path       :: The path to the ae used in reducing the qdata.
    """
    save_qsvm(qsvm, "qsvm_models/" + output_folder + "/qsvm_model")
