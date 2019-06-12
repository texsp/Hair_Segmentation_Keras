"""
Implement Fast Deep Matting for Portrait Animation on Mobile Phone
https://arxiv.org/abs/1707.08289
"""

from keras.layers import Input, Conv2D, Conv2DTranspose, DepthwiseConv2D, ReLU, Add, Activation, BatchNormalization, SeparableConv2D, UpSampling2D, MaxPooling2D, Concatenate, Multiply, Add
from keras.activations import relu
from keras.models import Model
from keras.layers import Lambda
from keras import backend as K
import tensorflow as tf


def _conv_bn(inputs, filters, kernel, strides, rate):
    x = Conv2D(filters, kernel, padding='same', strides=strides, dilation_rate=rate)(inputs)
    x = BatchNormalization(axis=-1)(x)
    x = ReLU(max_value=6)(x)
    return x


# ---------------- segmentation block -------------- #
# def segmentation_block(input_shape=(128, 128, 3), n_classes=1):
def FastDeepMatting(input_shape=(128, 128, 3), n_classes=1):
    inputs = Input(shape=input_shape)
    # segmentation block 
    d1 = _conv_bn(inputs, 13, 3, 2, 1)
    pool = MaxPooling2D((2,2))(inputs)
    c1 = Concatenate()([d1, pool])
    
    d2 = _conv_bn(c1, 16, 3, 1, 2)
    c2 = Concatenate()([d2, c1])

    d3 = _conv_bn(c2, 16, 3, 1, 4)
    c3 = Concatenate()([d3, c2])

    d4 = _conv_bn(c3, 16, 3, 1, 6)
    c4 = Concatenate()([d4, c3])

    d5 = _conv_bn(c4, 16, 3, 1, 8)
    c5 = Concatenate()([d2, d3, d4, d5])
    
    d6 = _conv_bn(c5, 2, 3, 1, 1)

    interp = UpSampling2D(size=(2,2), interpolation='bilinear')(d6)
    
    # feathering block    
    f, b = Lambda(lambda x: x[:,:,:,0:1])(interp), Lambda(lambda x: x[:,:,:,1:2])(interp)
    x_square = Lambda(lambda x: x*x)(inputs)
    f3 = Concatenate()([f,f,f])
    
    x_masked = Multiply()([inputs, f3])
    inputs2 = Concatenate()([inputs, interp, x_masked, x_square])
    
    c1= _conv_bn(inputs2, 32, 3, 1, 1)
    c2 = Conv2D(3, 3, padding='same', strides=1)(c1)
    
    w1, w2, b = Lambda(lambda x: x[:,:,:,0:1])(c2), Lambda(lambda x: x[:,:,:,1:2])(c2), Lambda(lambda x: x[:,:,:,2:3])(c2)
    output = Add()([Multiply()([w1, f]), Multiply()([w2, f])])
    output = Add()([output, b])
    output = Activation('sigmoid')(output)    
    model = Model(inputs, output)
    
    return model
    


# ----------------- feathering block --------------- #
def feather_block():

    seg_model = segmentation_block()
    x = seg_model.input
    out = seg_model.output
    foreground, background = tf.split(out, 2, -1)
    x_square = Lambda(lambda x: x**2)(x)
    f3 = tf.tile(foreground, multiples=(1,1,1,3)) 
    x_masked = Multiply()([x, f3])

    inputs = Concatenate()([x_masked, x, x_square, x_masked])
    
    # ?*?*?*11
    c1 = _conv_bn(inputs, 32, 3, 1, 1)
    c2 = Conv2D(3, 3, padding='same', strides=1)(c1)
    a, b, c = tf.split(c2, 3, -1)
    # a, b, c = K.expand_dims(c2[:,:,:,0], axis=-1), K.expand_dims(c2[:,:,:,1], axis=-1), K.expand_dims(c2[:,:,:,2], axis=-1)
    output = Add()([Multiply()([a, foreground]), Multiply()([b, background])])
    output = Add()([output, c])
    output = Activation('sigmoid')(output)
    model = Model(x, output)
    model.summary()

    
if __name__ == "__main__":
    model = segmentation_block()
    model.summary()
    # feather_block()

