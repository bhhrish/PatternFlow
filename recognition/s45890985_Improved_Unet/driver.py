import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import keras.backend as k

from model import *
from tensorflow.keras import datasets, layers, models, callbacks
from tensorflow.keras.utils import Sequence

WIDTH = 512
HEIGHT = 512
CHANNELS = 3


def load_img(img_path):
    # method taken and derived from Lab2 part 3 code
    # read and decode image to uint8 array
    image = tf.io.read_file(img_path)
    image = tf.image.decode_jpeg(image, channels=CHANNELS)

    # change img_path into coresponding mask_path
    mask_path = tf.strings.regex_replace(img_path, '-2_Training_Input', '_Training_GroundTruth')
    mask_path = tf.strings.regex_replace(mask_path, '.jpg', '_segmentation.png')

    # read and decode mask to uint8 array
    mask = tf.io.read_file(mask_path)
    mask = tf.image.decode_png(mask, channels=1, dtype=tf.uint8)

    # one hot encoding
    mask = tf.where(mask == 0, np.dtype('uint8').type(0), mask)
    mask = tf.where(mask != 0, np.dtype('uint8').type(1), mask)

    # normalise and reshape data
    # convert values from 0-255 to 0 - 1
    image = tf.cast(image, tf.float32) / 255.0
    mask = tf.cast(mask, tf.float32)

    # resize image to dims
    image = tf.image.resize(image, (WIDTH, HEIGHT))
    mask = tf.image.resize(mask, (WIDTH, HEIGHT))
    return image, mask


# calculates the dice coefficient of two images
def sdc(y_true, y_pred, smooth=1):
    intersection = k.sum(y_true * y_pred, axis=[1, 2, 3])
    union = k.sum(y_true, axis=[1, 2, 3]) + k.sum(y_pred, axis=[1, 2, 3])
    return k.mean((2. * intersection + smooth) / (union + smooth), axis=0)


# dice coefficient as a loos function
def sdc_loss(y_true, y_pred):
    return 1 - sdc(y_true, y_pred)


# displays one set of image, ground truth, predicted mask
def display_sample(display_list):
    # plot images side by side
    plt.figure(figsize=(20, 20))
    titles = ['Input Image', 'Ground Truth', 'Predicted Mask']
    n_col = min(len(display_list), 3)
    for col in range(n_col):
        plt.subplot(1, len(display_list), col + 1)
        plt.title(titles[col])
        plt.imshow(tf.keras.preprocessing.image.array_to_img(display_list[col]), cmap='gray')
        plt.axis('off')
    plt.show()


def display_prediction(model, dataset, num=1):
    # get a sample from dataset
    for image, mask in dataset.take(num):
        sample_image, sample_mask = image, mask

    # get prediction based on sample retrieved
    prediction = model.predict(sample_image[0][tf.newaxis, ...])
    prediction = np.round(prediction)

    # display samples side by side
    display_sample([sample_image[0], sample_mask[0], prediction[0]])

    # print the SDC of the true mask vs the predicted mask
    print('SDC: ' + str(sdc(sample_mask[0][tf.newaxis, ...], model.predict(sample_image[0][tf.newaxis, ...])).numpy()))


def main():
    # directories and parameters of dataset
    data_path = os.path.join("D:/UQ/2021 Sem 2/COMP3710/Report", "ISIC_2018\ISIC2018_Task1-2_Training_Input")
    data_size = len(os.listdir(data_path))
    training_size = int(np.ceil(data_size * 0.8))
    testing_size = data_size - training_size
    AUTOTUNE = tf.data.AUTOTUNE
    batch_size = 3
    # get a list of file names
    data_file_list = []
    for file in os.listdir(data_path):
        if file.endswith(".jpg"):
            data_file_list.append(os.path.join(data_path, file))

    # split data into train and test with a 80-20 split
    train_file_list = data_file_list[:training_size]
    test_file_list = data_file_list[training_size:]

    # initialise train and test datasets using file directories
    train_dataset = tf.data.Dataset.from_tensor_slices(train_file_list)
    test_dataset = tf.data.Dataset.from_tensor_slices(test_file_list)

    # map dataset to img and mask
    train_dataset = train_dataset.map(load_img, num_parallel_calls=AUTOTUNE)
    test_dataset = test_dataset.map(load_img, num_parallel_calls=AUTOTUNE)

    # print dataset shapes
    print(train_dataset)
    print(test_dataset)

    # shuffle, batch and augment training dataset
    train_dataset = train_dataset.shuffle(buffer_size=1000)
    train_dataset = train_dataset.repeat()
    train_dataset = train_dataset.batch(batch_size)
    train_dataset = train_dataset.prefetch(buffer_size=AUTOTUNE)

    # batch and prefetch testing dataset
    test_dataset = test_dataset.repeat()
    test_dataset = test_dataset.batch(batch_size)
    test_dataset = test_dataset.prefetch(buffer_size=AUTOTUNE)

    # create and compile unet model
    model = improved_unet(WIDTH, HEIGHT, CHANNELS)
    model.compile(optimizer='adam',loss=sdc_loss, metrics=['accuracy', sdc])
    model.summary()

    # training the model
    epochs = 5
    epoch_steps = training_size // batch_size
    test_steps = testing_size // batch_size
    history = model.fit(train_dataset, epochs=epochs, steps_per_epoch=epoch_steps,
                        validation_steps=test_steps, validation_data=test_dataset)


if __name__ == "__main__":
    main()
