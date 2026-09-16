
from src.model.training.two_tower_trainer import TwoTowerTrainer
from src.model.utils.utils import *
import os

def learning():
    model = TwoTowerTrainer(
        embedding_dim=64,
        learning_rate=3e-3,
        epochs=5,
        batch_size=4*1024
    )
    model.fit()
    return model


def main():
    model = learning()
     
    print("Training completed successfully.")
    model.save_model(save_dir="artifacts")
    print("Model saved successfully.")

if __name__ == "__main__":
   main()
   