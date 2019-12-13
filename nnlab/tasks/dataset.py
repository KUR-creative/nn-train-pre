from glob import glob

import os
import cv2
import numpy as np
from bidict import bidict
import tensorflow as tf
from tqdm import tqdm
import deal

from nnlab.utils import fp
from nnlab.data import image as im #image util

def _bytes_feature(value):
    """Returns a bytes_list from a string / byte."""
    if isinstance(value, type(tf.constant(0))):
        value = value.numpy() # BytesList won't unpack a string from an EagerTensor.
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))
def _float_feature(value):
    """Returns a float_list from a float / double."""
    return tf.train.Feature(float_list=tf.train.FloatList(value=[value]))
def _int64_feature(value):
    """Returns an int64_list from a bool / enum / int / uint."""
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


@deal.pre(lambda imgs, masks, *_: 
    len(imgs) == len(masks), message='len(img_paths) != len(mak_paths)')
@deal.pre(lambda imgs, masks, *_: 
    (all(map(lambda p: os.path.exists(p), imgs)) and
     all(map(lambda p: os.path.exists(p), masks))),
    message='some file path are not exist')
def generate(img_paths, mask_paths, src_dst_colormap, 
        out_path, look_and_feel_check=False):
    '''
    Generate dataset using images from `img_paths`, masks from `mask_paths`.
    Masks are mapped by src_dst_colormap. Finally, dataset is saved to `out_path`.

    if look_and_feel_check == True, load and display 
    image and masks in generated dataset.

    Image, mask are must be paired, and exists.
    '''

    imgseq = fp.map(cv2.imread, img_paths)
    maskseq = fp.map(
        fp.pipe(cv2.imread, im.map_colors(src_dst_colormap)), mask_paths)

    # Create and save tfrecords dataset.
    def datum_example(img_bin, mask_bin):
        h,w,c   = img_bin.shape
        mh,mw,_ = mask_bin.shape
        assert h == mh and w == mw, 'img.h,w = {} != {} mask.h,w'.format(
            img_bin.shape[:2], mask_bin.shape[:2])

        feature = {
            'h': _int64_feature(h),
            'w': _int64_feature(w),
            'c': _int64_feature(c),
            'mc': _int64_feature(len(src_dst_colormap)), # mask channels
            'img': _bytes_feature(img_bin.tobytes()),
            'mask': _bytes_feature(mask_bin.tobytes()),
        }

        return tf.train.Example(features=tf.train.Features(feature=feature))

    
    with tf.io.TFRecordWriter(out_path) as writer:
        #for img_bin, mask_bin in tqdm(fp.take(4,zip(imgseq, maskseq)), total=4):
        for img_bin, mask_bin in tqdm(zip(imgseq, maskseq), total=len(img_paths)):
            tf_example = datum_example(img_bin, mask_bin)
            writer.write(tf_example.SerializeToString())

    if look_and_feel_check:
        def parse_single_example(example):
            return tf.io.parse_single_example(
                example,
                {'h': tf.io.FixedLenFeature([], tf.int64),
                 'w': tf.io.FixedLenFeature([], tf.int64),
                 'c': tf.io.FixedLenFeature([], tf.int64),
                 'mc': tf.io.FixedLenFeature([], tf.int64),
                 'img': tf.io.FixedLenFeature([], tf.string),
                 'mask': tf.io.FixedLenFeature([], tf.string)})
        # Load saved tfrecords dataset
        snet_dset = tf.data.TFRecordDataset(out_path)
        parsed_snet_dset = snet_dset.map(parse_single_example)

        # Display image, maskss
        for no, datum in enumerate(parsed_snet_dset): 
            h = datum['h'].numpy()
            w = datum['w'].numpy()
            c = datum['c'].numpy()
            mc = datum['mc'].numpy()
            img_raw = datum['img'].numpy()
            mask_raw = datum['mask'].numpy()

            #img = Image.open(io.BytesIO(img_raw))
            img  = np.frombuffer(img_raw, dtype=np.uint8).reshape((h,w,c))
            mask = np.frombuffer(mask_raw, dtype=np.uint8).reshape((h,w,mc))

            cv2.imshow('im', img)
            #cv2.imshow('mask', im.map_colors(src_dst_colormap.inverse, mask).astype(np.float64))
            cv2.waitKey(0)


if __name__ == '__main__':
    src_dst_colormap = bidict({
        (255,  0,  0): (0,0,1),
        (  0,  0,255): (0,1,0),
        (  0,  0,  0): (1,0,0)})
    dataset.generate(
        './dataset/snet285/image',
        './dataset/snet285/clean_rbk',
        './dataset/test.tfrecords',
        rbk_src_dst)