"""
Reader using cv2.
"""
from __future__ import division
from __future__ import print_function
import os
import math
import random
import functools
import numpy as np
import paddle
import cv2

random.seed(0)
np.random.seed(0)

DATA_DIM = 224

THREAD = 8
BUF_SIZE = 102400

DATA_DIR = 'data/ILSVRC2012'
img_mean = np.array([0.485, 0.456, 0.406]).reshape((3, 1, 1))
img_std = np.array([0.229, 0.224, 0.225]).reshape((3, 1, 1))


def rotate_image(img):
    """ rotate_image """
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    angle = np.random.randint(-10, 11)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(img, matrix, (w, h))
    return rotated


def random_crop(img, size, scale=(0.08, 1.0), ratio=(3./4., 4./3.)):
    """ random_crop """
    aspect_ratio = math.sqrt(np.random.uniform(*ratio))
    w = 1. * aspect_ratio
    h = 1. / aspect_ratio

    bound = min((float(img.shape[0]) / img.shape[1]) / (w**2), (float(img.shape[1]) / img.shape[0]) / (h**2))
    scale_max = min(scale[1], bound)
    scale_min = min(scale[0], bound)

    target_area = img.shape[0] * img.shape[1] * np.random.uniform(scale_min, scale_max)
    target_size = math.sqrt(target_area)
    w = int(target_size * w)
    h = int(target_size * h)
    i = np.random.randint(0, img.shape[0] - w + 1)
    j = np.random.randint(0, img.shape[1] - h + 1)

    img = img[i:i + w, j:j + h, :]

    img = cv2.resize(img, (size, size), interpolation=cv2.INTER_LANCZOS4)
    return img


def distort_color(img):
    return img


def resize_short(img, target_size):
    """ resize_short """
    percent = float(target_size) / min(img.shape[0], img.shape[1])
    resize_width = int(round(img.shape[1] * percent))
    resize_height = int(round(img.shape[0] * percent))
    img = cv2.resize(img, (resize_width, resize_height), interpolation=cv2.INTER_LANCZOS4)
    return img


def crop_image(img, target_size, center):
    """ crop_image """
    height, width = img.shape[:2]
    size = target_size
    if center:
        w_start = (width - size) // 2
        h_start = (height - size) // 2
    else:
        w_start = np.random.randint(0, width - size + 1)
        h_start = np.random.randint(0, height - size + 1)
    w_end = w_start + size
    h_end = h_start + size
    img = img[h_start:h_end, w_start:w_end, :]
    return img


def process_image(sample,
                  mode,
                  color_jitter,
                  rotate,
                  mean=img_mean,
                  std=img_std):
    """ process_image """
    img_path = sample[0]
    img = cv2.imread(img_path)

    if mode == 'train':
        if rotate:
            img = rotate_image(img)
        img = random_crop(img, DATA_DIM)
        if color_jitter:
            img = distort_color(img)
        if np.random.randint(0, 2) == 1:
            img = img[:, ::-1, :]
    else:
        img = resize_short(img, target_size=256)
        img = crop_image(img, target_size=DATA_DIM, center=True)

    img = img[:, :, ::-1].astype('float32').transpose((2, 0, 1)) / 255
    img -= mean
    img /= std

    if mode == 'train' or mode == 'val':
        return img, sample[1]
    elif mode == 'test':
        return img,
    else:
        raise ValueError("Unknown mode {}".format(mode))


def _reader_creator(file_list,
                    mode,
                    shuffle=False,
                    color_jitter=False,
                    rotate=False,
                    data_dir=DATA_DIR,
                    pass_id_as_seed=1,
                    num_threads=THREAD):
    def reader():
        with open(file_list) as f_list:
            full_lines = [line.strip() for line in f_list]
            if shuffle:
                np.random.seed(pass_id_as_seed)
                np.random.shuffle(full_lines)

            for line in full_lines:
                if mode == 'train' or mode == 'val':
                    img_path, label = line.split()
                    img_path = img_path.replace("JPEG", "jpeg")
                    img_path = os.path.join(data_dir, 'train', img_path)
                    yield img_path, int(label)
                elif mode == 'test':
                    img_path, label = line.split()
                    img_path = img_path.replace("JPEG", "jpeg")
                    img_path = os.path.join(data_dir, 'val', img_path)
                    yield [img_path]

    image_mapper = functools.partial(
        process_image,
        mode=mode,
        color_jitter=color_jitter,
        rotate=rotate)
    reader = paddle.reader.xmap_readers(
        image_mapper, reader, num_threads, BUF_SIZE, order=False)
    return reader


def train(data_dir=DATA_DIR, pass_id_as_seed=1, num_threads=THREAD):
    file_list = os.path.join(data_dir, 'train.txt')
    return _reader_creator(
        file_list,
        'train',
        shuffle=True,
        color_jitter=False,
        rotate=False,
        data_dir=data_dir,
        pass_id_as_seed=pass_id_as_seed,
        num_threads=num_threads)
