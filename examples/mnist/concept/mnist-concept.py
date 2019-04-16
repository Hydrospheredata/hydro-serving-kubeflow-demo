import os
import shutil
import numpy as np
import tensorflow as tf


# Training Parameters
learning_rate = float(os.environ.get("LEARNING_RATE", 0.01))
num_steps = int(os.environ.get("LEARNING_STEPS", 10000))
batch_size = int(os.environ.get("BATCH_SIZE", 256))
display_step = int(os.environ.get("DISPLAY_STEPS", 1000))

models_path = os.environ.get("MNIST_MODELS_DIR", "models/mnist")
models_path = os.path.join(models_path, "concept")
base_path = os.environ.get("MNIST_DATA_DIR", "data/mnist")
train_file = "train.npz"

# Network Parameters
num_hidden_1 = 256 
num_hidden_2 = 128 
num_input = 784


# Import MNIST data
with np.load(os.path.join(base_path, train_file)) as data:
    imgs, labels = data["imgs"], data["labels"]

dataset = tf.data.Dataset.from_tensor_slices((imgs, labels))
dataset = dataset.batch(batch_size).repeat()
iterator = dataset.make_one_shot_iterator()
imgs, labels = iterator.get_next()


weights = {
    'encoder_h1': tf.Variable(tf.random_normal([num_input, num_hidden_1])),
    'encoder_h2': tf.Variable(tf.random_normal([num_hidden_1, num_hidden_2])),
    'decoder_h1': tf.Variable(tf.random_normal([num_hidden_2, num_hidden_1])),
    'decoder_h2': tf.Variable(tf.random_normal([num_hidden_1, num_input])),
}
biases = {
    'encoder_b1': tf.Variable(tf.random_normal([num_hidden_1])),
    'encoder_b2': tf.Variable(tf.random_normal([num_hidden_2])),
    'decoder_b1': tf.Variable(tf.random_normal([num_hidden_1])),
    'decoder_b2': tf.Variable(tf.random_normal([num_input])),
}

def encoder(x):
    layer_1 = tf.nn.sigmoid(tf.add(tf.matmul(x, weights['encoder_h1']), biases['encoder_b1']))
    layer_2 = tf.nn.sigmoid(tf.add(tf.matmul(layer_1, weights['encoder_h2']), biases['encoder_b2']))
    return layer_2

def decoder(x):
    layer_1 = tf.nn.sigmoid(tf.add(tf.matmul(x, weights['decoder_h1']), biases['decoder_b1']))
    layer_2 = tf.nn.sigmoid(tf.add(tf.matmul(layer_1, weights['decoder_h2']), biases['decoder_b2']))
    return layer_2

imgs_flattened = tf.layers.flatten(imgs)
encoder_op = encoder(imgs_flattened)
decoder_op = decoder(encoder_op)

y_pred, y_true = decoder_op, imgs_flattened
loss = tf.reduce_mean(tf.pow(y_true - y_pred, 2), axis=-1)
reconstructed = tf.expand_dims(loss, -1)
optimizer = tf.train.AdamOptimizer(learning_rate).minimize(loss)


with tf.Session() as sess:
    sess.run(tf.global_variables_initializer())

    # Training
    for i in range(1, num_steps+1):
        _, l = sess.run([optimizer, loss])
        if i % display_step == 0 or i == 1:
            print(f'Step {i}: Minibatch Loss: {np.mean(l)}')

    # Save model
    signature_map = {
        "infer": tf.saved_model.signature_def_utils.predict_signature_def(
            inputs={
                "imgs": imgs,
                "probabilities": tf.placeholder(dtype=tf.float32, shape=(None, 10)),
                "class_ids": tf.placeholder(dtype=tf.int64, shape=(None, 1)),
                "logits": tf.placeholder(dtype=tf.float32, shape=(None, 10)),
                "classes": tf.placeholder(dtype=tf.string, shape=(None, 1)),
            }, 
            outputs={"reconstructed": reconstructed})
    }

    shutil.rmtree(models_path, ignore_errors=True)
    builder = tf.saved_model.builder.SavedModelBuilder(models_path)
    builder.add_meta_graph_and_variables(
        sess=sess, 
        tags=[tf.saved_model.tag_constants.SERVING],
        signature_def_map=signature_map)
    builder.save()