import os
from keras import backend as keras
import keras
from keras import backend as K
from keras.applications.vgg19 import VGG19
from drop_block import DropBlock2D

from keras.layers import Conv2D, UpSampling2D, MaxPooling2D, Dropout
from keras.layers import Input

from keras.layers.core import Activation

from keras.models import Model
from keras.optimizers import Adam
from keras.layers.merge import Concatenate
os.environ['KERAS_BACKEND'] = 'tensorflow'
K.set_image_dim_ordering('tf')

def vgg19():
    inputs = Input((128, 128, 3))
    b_model = VGG19(weights='imagenet', include_top=False, input_tensor=inputs)
    model_vgg19 = Model(inputs=b_model.input, outputs=[ b_model.get_layer('block1_conv2').output,
                                                        b_model.get_layer('block2_conv2').output,
                                                        b_model.get_layer('block2_pool').output])
    return model_vgg19
def unet(vgg):
    input_1 = Input((128, 128, 3))
    conv1, conv2, pool2 = vgg(input_1)
    conv1 = DropBlock2D(block_size=5, keep_prob=0.5)(conv1)
    conv2 = DropBlock2D(block_size=5, keep_prob=0.5)(conv2)
    # pool2 = DropBlock2D(block_size=5, keep_prob=0.5)(pool2)
    # conv1 = Dropout(0.5)(conv1)
    # conv2 = Dropout(0.5)(conv2)
    # pool2 = Dropout(0.5)(pool2)
    conv3 = Conv2D(256, 3, padding='same', kernel_initializer='he_normal')(pool2)
    conv3 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(conv3)
    conv3 = Activation('relu')(conv3)
    conv3 = Conv2D(256, 3, padding='same', kernel_initializer='he_normal')(conv3)
    conv3 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(conv3)
    conv3 = Activation('relu')(conv3)
    drop3 = DropBlock2D(block_size=5, keep_prob=0.5, name='Dropout3')(conv3)
    #drop3 = Dropout(0.5)(conv3)

    up4 = Conv2D(128, 2, padding='same', kernel_initializer='he_normal')(UpSampling2D(size=(2, 2))(drop3))
    up4 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(up4)
    up4 = Activation('relu')(up4)
    merge4 = keras.layers.Concatenate(axis=3)([conv2, up4])
    conv4 = Conv2D(128, 3, padding='same', kernel_initializer='he_normal')(merge4)
    conv4 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(conv4)
    conv4 = Activation('relu')(conv4)
    conv4 = Conv2D(128, 3, padding='same', kernel_initializer='he_normal')(conv4)
    conv4 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(conv4)
    conv4 = Activation('relu')(conv4)
    conv4 = DropBlock2D(block_size=5, keep_prob=0.5)(conv4)
    #conv4 = Dropout(0.5)(conv4)

    up5 = Conv2D(64, 2, padding='same', kernel_initializer='he_normal')(UpSampling2D(size=(2, 2))(conv4))
    up5 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(up5)
    up5 = Activation('relu')(up5)
    merge5 = keras.layers.Concatenate(axis=3)([conv1, up5])
    conv5 = Conv2D(64, 3, padding='same', kernel_initializer='he_normal')(merge5)
    conv5 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(conv5)
    conv5 = Activation('relu')(conv5)
    conv5 = Conv2D(64, 3, padding='same', kernel_initializer='he_normal')(conv5)
    conv5 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(conv5)
    conv5 = Activation('relu')(conv5)
    conv5 = DropBlock2D(block_size=5, keep_prob=0.5)(conv5)
    #conv5 = Dropout(0.5)(conv5)
    conv5 = Conv2D(2, 3, padding='same', kernel_initializer='he_normal')(conv5)
    conv5 = keras.layers.normalization.BatchNormalization(axis=3, epsilon=1e-6)(conv5)
    conv5 = Activation('relu')(conv5)


    conv6 = Conv2D(1, 1, activation='sigmoid')(conv5)

    def jd_loss(y_true, y_pred):
        y_true = keras.layers.Reshape([-1])(y_true)
        y_pred = keras.layers.Reshape([-1])(y_pred)
        tp = keras.layers.Multiply()([y_true, y_pred])
        tp = K.sum(tp, axis=1)
        t = keras.layers.Multiply()([y_true, y_true])
        t = K.sum(t, axis=1)
        p = keras.layers.Multiply()([y_pred, y_pred])
        p = K.sum(p, axis=1)
        temp = keras.layers.Subtract()([(keras.layers.Add()([t, p])), tp])
        # temp = keras.layers.Add()([temp, 1e-9])
        # temp = 1/temp
        # temp = keras.layers.Multiply()([tp,temp])
        jd_l = 1 - (tp / (temp + 1e-9))
        return jd_l

    model = Model(inputs=input_1, outputs=conv6)

    model.compile(optimizer=Adam(lr=1e-3), loss = jd_loss, metrics=['accuracy'])

    return model