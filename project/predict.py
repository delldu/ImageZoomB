"""Model predict."""# coding=utf-8
#
# /************************************************************************************
# ***
# ***    Copyright Dell 2020, All Rights Reserved.
# ***
# ***    File Author: Dell, 2020年 11月 30日 星期一 22:50:05 CST
# ***
# ************************************************************************************/
#
import argparse
import glob
import os
import pdb

import torch
import torchvision.transforms as transforms
from PIL import Image
from tqdm import tqdm
from data import gaussian_batch
from model import enable_amp, get_model, model_device, model_load

if __name__ == "__main__":
    """Predict."""

    parser = argparse.ArgumentParser()
    parser.add_argument('--checkpoint', type=str,
                        default="models/ImageZoom_X4.pth", help="checkpint file")
    parser.add_argument('--input', type=str,
                        default="dataset/predict/LR/*.png", help="input image")
    parser.add_argument('--scale', type=int, default=2, help="scale factor")
    parser.add_argument('--output', type=str,
                        default="dataset/predict/HR", help="output directory")

    args = parser.parse_args()

    if (args.scale == 2):
        args.checkpoint = "models/ImageZoom_X2.pth"

    model = get_model(scale=args.scale)
    model_load(model, args.checkpoint)
    device = model_device()
    model.to(device)
    model.eval()

    enable_amp(model)

    totensor = transforms.ToTensor()
    toimage = transforms.ToPILImage()

    image_filenames = glob.glob(args.input)
    progress_bar = tqdm(total=len(image_filenames))

    gaussian_scale = 1
    for index, filename in enumerate(image_filenames):
        progress_bar.update(1)

        image = Image.open(filename).convert("RGB")
        input_tensor = totensor(image).unsqueeze(0).to(device)

        B,C,H,W = input_tensor.size()
        zshape = [B, C * (args.scale**2 - 1), H, W]

        with torch.no_grad():
            output_tensor = model(input_tensor)
            y_forw = torch.cat((input_tensor, gaussian_scale * gaussian_batch(zshape).to(device)), dim=1)
            output_tensor = model(x=y_forw, rev=True)[:, :3, :, :]

        output_tensor.clamp_(0, 1.0)
        output_tensor = output_tensor.squeeze(0)

        toimage(output_tensor.cpu()).save(
            "{}/{}".format(args.output, os.path.basename(filename)))

        del input_tensor, output_tensor
        torch.cuda.empty_cache()
