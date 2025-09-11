#
# This script takes the models given to it, converts them to serialized TorchScript versions, 
# which can then be loaded without having to bundle all of torch with the app.
#


import torch

unet_mosquito = torch.load(r"D:\USDA-Auburn\CS-Repository\GUI\models\unet_mosquito.py")
unet_probesplitter = torch.load(r"D:\USDA-Auburn\CS-Repository\GUI\models\unet_probesplitter.py")
unet_sharpshooter = torch.load(r"D:\USDA-Auburn\CS-Repository\GUI\models\unet_sharpshooter.py")



for i, model in enumerate([unet_mosquito, unet_probesplitter, unet_sharpshooter]):
    model.eval()
    example_input = torch.randn(1, input_size)  # match your model input
    traced = torch.jit.trace(model, example_input)
    traced.save(f"model_{i}_traced.pt")