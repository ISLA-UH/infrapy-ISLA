import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
import tensorflow as tf
import os
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models
def build_ims_net(input_shape=(6, 64, 64, 10)) -> tf.keras.Model:
    """
    Build the improved multiscale network (Not to be confused with infrasound monitoring system) for ConvLTSM structure

    Parameters
    ----------
    input_shape: tuple 
        Shape of the data stack (Sequences, Width, Height, Channels)

    Returns:
    ----------
    ret_model : tf.keras.Model
        Keras model of the improved multiscale ConvLTSM network

    """
    inputs = layers.Input(shape=input_shape)

    # 3x3 kernels
    b1 = layers.ConvLSTM2D(16, (3, 3), padding='same', return_sequences=True)(inputs)
    
    # 5x5 kernels
    b2 = layers.ConvLSTM2D(16, (5, 5), padding='same', return_sequences=True)(inputs)
    
    # 7x7 kernels
    b3 = layers.ConvLSTM2D(16, (7, 7), padding='same', return_sequences=True)(inputs)

    # Combine branches
    merged = layers.Concatenate()([b1, b2, b3])

    # Further Final ConvLSTM Layer
    x = layers.ConvLSTM2D(64, (3, 3), padding='same', return_sequences=False)(merged)
    x = layers.BatchNormalization()(x)
    x = layers.Flatten()(x)
    
    #  Dense Layer
    x = layers.Dense(128, activation='relu')(x)
    x = layers.Dropout(0.5)(x)

    # Outputs
    out_class = layers.Dense(1, activation='sigmoid', name='class_out')(x)

    ret_model = models.Model(inputs=inputs, outputs=[out_class])
    return ret_model

"""
Code Starts Here
"""
path = 'sandbox\\gaf_classification\\training\\numpy\\'

X_data = np.load(os.path.join(path, 'X_train_cwt_5D.npy'))  # Data is X
Y_nonint = np.load(os.path.join(path, 'Y_train_cwt_labels.npy'))  # Labels are Y

Y_labels = np.array([])
for label in Y_nonint:
    if label == 'sonicboom':
        label = 0
    else:
        label = 1
    Y_labels = np.append(Y_labels, label)
X_data = X_data.transpose(0, 1, 3, 4, 2) # Reshape data for ConvLTSM so read it more efficiently

training_set = X_data[:2250]   # 2250 samples for training. Tradeoff between training and test/validation size
test_set = X_data[2250:]      # Remaining samples for testing (Limited test & validation data available.)


training_labels = Y_labels[:2250]
test_labels = Y_labels[2250:]
X_train = training_set
Y_train = training_labels
all_indices = np.arange(len(X_data))
test_indices = all_indices[2250:]


# Split test set into test and validation sets
#X_val, X_test, Y_val, Y_test, val_idx, test_idx = train_test_split(test_set, test_labels, test_indices, test_size=0.5, random_state=42)
X_val = test_set[:300]
Y_val = test_labels[:300]
X_test = test_set[300:]
Y_test = test_labels[300:]
test_idx = test_indices[300:]
print(f"Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")

#  Build and compile the model
model = build_ims_net()
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.000005),
    loss={
        'class_out': 'binary_crossentropy',
    },
    loss_weights={
        'class_out': 1.0,
    },
    metrics={'class_out': 'accuracy'}
)
#  If overfitting occurs, stop early
callbacks = [
    tf.keras.callbacks.EarlyStopping(
        monitor='val_loss',
        patience=5, 
        restore_best_weights=True
    )
]

reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
    monitor='val_loss', factor=0.5, patience=5, min_lr=0.000001
)

checkpoint = tf.keras.callbacks.ModelCheckpoint(
    'best_model.h5',
    monitor='val_class_out_accuracy',
    save_best_only=True,
    mode='max'
)
print(Y_train.shape)
print(type(Y_train))
history = model.fit(
    X_train, 
    Y_train,
    validation_data=(X_val, Y_val),
    epochs=10,
    batch_size=16,
    callbacks=[reduce_lr, checkpoint] 
)

model.load_weights('best_model.h5') 
results = model.evaluate(X_test, {
    'class_out': Y_test
})

print(f"Final Test Accuracy: {results[1]}")

# Get predictions
preds = model.predict(X_test)
y_pred_class = (preds > 0.5).astype(int)
y_true_class = Y_test

print(confusion_matrix(y_true_class, y_pred_class))
print(classification_report(y_true_class, y_pred_class))
plt.title('Classification Accuracy - 64pt GAF')
plt.legend()
plt.show()

#  Currently not working, this is supposed to plot the false positives/negatives for debugging purposes
"""
# Identify False Positives/Negatives
fp_indices = np.where((y_true_class == 0) & (y_pred_class == 1))[0]
fn_indices = np.where((y_true_class == 1) & (y_pred_class == 0))[0]
with open('sandbox\\gaf_classification\\training\\numpy\\all_entries.pkl', 'rb') as f:
    all_entries = pickle.load(f)
try:
    # Call your plotting function
    plot_error_samples(
        indices=fp_indices, 
        title="False Positives: Noise called Signal",
        data_x=X_test,
        meta_indices=test_idx, # This is the map
        entries=all_entries    # This is the file cabinet
    )
except Exception as e:
    print(f"Error plotting False Positives: {e}")
"""
