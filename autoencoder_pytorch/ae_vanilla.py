# The vanilla autoencoder architecture. Reduces the number
# of features from 67 down to 16 by using a combination of linear and ELU
# layers. The loss function of the autoencoder is the MSE between the
# histograms reconstructed by the decoder and the original variables.

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from pytorch_model_summary import summary
import os, json
import matplotlib.pyplot as plt

from terminal_colors import tcols

seed = 100
torch.manual_seed(seed)

# Diagnosis tools. Enable in case you need.
torch.autograd.set_detect_anomaly(False)
torch.autograd.profiler.profile(enabled=False)

class AE_vanilla(nn.Module):
    def __init__(self, device='cpu', hparams={}):

        super().__init__()
        self.hp = {
            "ae_type"    : "vanilla",
            "ae_layers"  : [67, 64, 52, 44, 32, 24, 16],
            "lr"         : 0.002,
            "enc_activ"  : 'nn.Tanh()',
            "dec_activ"  : 'nn.Tanh()',
        }
        self.device    = device
        exec('self.enc_activ = ' + self.hp["enc_activ"])
        exec('self.dec_activ = ' + self.hp["dec_activ"])

        self.recon_loss_function = nn.MSELoss(reduction='mean')
        self.hp.update((k, hparams[k]) for k in self.hp.keys() & hparams.keys())

        self.best_valid_loss = 9999
        self.all_train_loss  = []
        self.all_valid_loss  = []

        self.early_stopping_limit = 10
        self.epochs_no_improve    = 0

        self.encoder = \
            self.construct_encoder(self.hp['ae_layers'], self.enc_activ)
        self.decoder = \
            self.construct_decoder(self.hp['ae_layers'], self.dec_activ)

        self = self.to(device)
        self.optimizer = optim.Adam(self.parameters(), lr=self.hp['lr'])

    @staticmethod
    def construct_encoder(layers, en_activ):
        """
        Construct the encoder layers.
        """
        enc_layers = []
        layer_nbs = range(len(layers))
        for idx in layer_nbs:
            enc_layers.append(nn.Linear(layers[idx], layers[idx+1]))
            if idx == len(layers) - 2 and en_activ is None: break
            if idx == len(layers) - 2: enc_layers.append(en_activ); break
            enc_layers.append(nn.ELU(True))

        return nn.Sequential(*enc_layers)

    @staticmethod
    def construct_decoder(layers, dec_activ):
        """
        Construct the decoder layers.
        """
        dec_layers = []
        layer_nbs = reversed(range(len(layers)))
        for idx in layer_nbs:
            dec_layers.append(nn.Linear(layers[idx], layers[idx-1]))
            if idx == 1 and dec_activ is None: break
            if idx == 1 and dec_activ: dec_layers.append(dec_activ); break
            dec_layers.append(nn.ELU(True))

        return nn.Sequential(*dec_layers)

    def forward(self, x):
        latent = self.encoder(x)
        reconstructed = self.decoder(latent)
        return latent, reconstructed

    def compute_loss(self, x_data, y_data):
        if type(x_data) is np.ndarray:
            x_data = torch.from_numpy(x_data).to(self.device)
        latent, recon = self.forward(x_data.float())
        return self.recon_loss_function(recon, x_data.float())

    @staticmethod
    def print_losses(epoch, epochs, train_loss, valid_loss):
        print(f"Epoch : {epoch + 1}/{epochs}, "
              f"Train loss (average) = {train_loss.item():.8f}")
        print(f"Epoch : {epoch + 1}/{epochs}, "
              f"Valid loss = {valid_loss.item():.8f}")

    @staticmethod
    def print_summary(model, device):
        try:
            summary(model, torch.Tensor(model[0].in_features).to(device),
                show_input=True, show_hierarchical=False, print_summary=True,
                max_depth=1, show_parent_layers=False)
        except:
            print(tcols.WARNING +
                  "Net summary failed! Probs using BatchNorm layers!"
                  + tcols.ENDC)

    def network_summary(self):
        print(tcols.OKGREEN + "Encoder summary:" + tcols.ENDC)
        self.print_summary(self.encoder, self.device)
        print('\n')
        print(tcols.OKGREEN + "Decoder summary:" + tcols.ENDC)
        self.print_summary(self.decoder, self.device)
        print('\n\n')

    def optimizer_summary(self):
        print(tcols.OKGREEN + "Optimizer summary:" + tcols.ENDC)
        print(self.optimizer)
        print('\n\n')

    def save_best_loss_model(self, valid_loss, outdir):
        if self.best_valid_loss > valid_loss:
            self.epochs_no_improve = 0
            print(tcols.OKGREEN + f"New min: {self.best_valid_loss:.2e}" +
                  tcols.ENDC)

            self.best_valid_loss = valid_loss
            if not outdir is None:
                torch.save(self.state_dict(), outdir + 'best_model.pt')

        else: self.epochs_no_improve += 1

    def early_stopping(self):
        if self.epochs_no_improve >= self.early_stopping_limit:
            return 1
        return 0

    @torch.no_grad()
    def valid(self, valid_loader, outdir):
        # Evaluate the validation loss for the model and save if new minimum.

        x_data_valid, y_data_valid = iter(valid_loader).next()
        x_data_valid = x_data_valid.to(self.device)
        self.eval()

        loss = self.compute_loss(x_data_valid, None)
        self.save_best_loss_model(loss, outdir)

        return loss

    def train_batch(self, x_batch, y_batch=None):
        # Train the model on a batch and evaluate the different kinds of losses.
        # Propagate this backwards for minimum train_loss.

        feature_size  = x_batch.shape[1]
        init_feats    = x_batch.view(-1,feature_size).to(self.device)
        if not y_batch is None: y_batch = y_batch.to(self.device)

        loss = self.compute_loss(init_feats, y_batch)

        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()

        return loss

    def train_all_batches(self, train_loader):
        # Train the autoencoder on all the batches.

        batch_loss_sum = 0
        nb_of_batches  = 0
        for batch in train_loader:
            x_batch, y_batch = batch
            batch_loss       = self.train_batch(x_batch)
            batch_loss_sum   += batch_loss
            nb_of_batches    += 1

        return batch_loss_sum/nb_of_batches

    def train_autoencoder(self, train_loader, valid_loader, epochs, outdir):

        self.network_summary(); self.optimizer_summary()
        print(tcols.OKCYAN + "Training the vanilla AE model..." + tcols.ENDC)

        for epoch in range(epochs):
            self.train()

            train_loss = self.train_all_batches(train_loader)
            valid_loss = self.valid(valid_loader, outdir)
            if self.early_stopping(): break

            self.all_train_loss.append(train_loss.item())
            self.all_valid_loss.append(valid_loss.item())
            self.print_losses(epoch, epochs, train_loss, valid_loss)

    def loss_plot(self, outdir):
        # Plots the loss for each epoch for the training and validation data.

        epochs = list(range(len(self.all_train_loss)))
        plt.plot(epochs, self.all_train_loss,
            color="gray", label="Training Loss (average)")
        plt.plot(epochs, self.all_valid_loss,
            color="chartreuse", label="Validation Loss")
        plt.xlabel("Epochs"); plt.ylabel("Loss")

        plt.text(np.min(epochs), np.max(self.all_train_loss),
            f"Min: {self.best_valid_loss:.2e}", verticalalignment='top',
            horizontalalignment='left', color='green', fontsize=15,
            bbox={'facecolor': 'white', 'alpha': 0.8, 'pad': 5})

        plt.legend()
        plt.savefig(outdir + "loss_epochs.pdf")
        plt.close()

        print(tcols.OKGREEN + f"Loss vs epochs plot saved to {outdir}." +
              tcols.ENDC)

    def export_architecture(self, outdir):
        # Saves the structure of the nn to a file.
        with open(outdir + 'model_architecture.txt', 'w') as model_architecture:
            print(self, file=model_architecture)

    def export_hyperparameters(self, outdir):
        # Saves the hyperparameters of the model to a json file.
        file_path   = os.path.join(outdir, 'hyperparameters.json')
        params_file = open(file_path, 'w')
        json.dump(self.hp, params_file)
        params_file.close()

    def load_model(self, model_path):
        # Loads the weights of a trained model saved in a .pt file.
        model_path = os.path.join(model_path, 'best_model.pt')
        if not os.path.exists(model_path): raise FileNotFoundError("∄ path.")
        self.load_state_dict(
            torch.load(model_path, map_location=torch.device(self.device)))

    @torch.no_grad()
    def predict(self, x_data):
        # Compute the prediction of the autoencoder, given input np array x.
        x_data = torch.from_numpy(x_data).to(self.device)
        self.eval()
        latent, reconstructed = self.forward(x_data.float())

        latent        = latent.cpu().numpy()
        reconstructed = reconstructed.cpu().numpy()
        return latent, reconstructed