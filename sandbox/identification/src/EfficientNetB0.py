import numpy as np
from sklearn.metrics import confusion_matrix, classification_report
import tensorflow as tf
import os
import matplotlib.pyplot as plt
from tensorflow.keras import layers, models
from tensorflow.keras.callbacks import ReduceLROnPlateau
from tensorflow.keras.applications import EfficientNetB0
from tensorflow.keras.applications.efficientnet import preprocess_input

# Custom preprocessing layer class to handle EfficientNets expected inputs 
@tf.keras.utils.register_keras_serializable(package="Custom", name="EfficientNetPreprocessing")
class EfficientNetPreprocessing(layers.Layer):
    """Custom preprocessing layer for EfficientNet that can be serialized."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def call(self, inputs):
        x = inputs * 255.0
        return preprocess_input(x)

    def get_config(self):
        return super().get_config()


def build_efficientnetb0(input_shape=(256, 256, 1), num_classes=2):
    """
    EfficientNet-B0 with ImageNet pre-trained weights for binary classification.
    Parameters:
    ----------
    input_shape : Tuple
        Shape of the input data (height, width, channels)
    num_classes : int
        Number of output classes (2 for binary classification)
    
    Returns:
    ---------
    model : tf.keras.Model
        Compiled EfficientNet-B0 model
    base_model : tf.keras.Model
        EfficientNet-B0 model without classification head for finetuning

    """

    inputs = layers.Input(shape=input_shape)

    # First stem takes 1 channel and transforms it to match format of efficientnet pretrained weights
    x = layers.Conv2D(16, 3, padding='same', use_bias=False)(inputs)
    x = layers.BatchNormalization()(x)
    x = layers.ReLU()(x)
    x = layers.Conv2D(3, 1, padding='same', use_bias=False)(x)
    x = EfficientNetPreprocessing()(x)
    # Load pre-trained EfficientNet-B0 backbone
    base_model = EfficientNetB0(
        include_top=False,
        weights='imagenet',
        input_shape=(input_shape[0], input_shape[1], 3),
        pooling='avg'
    )
    base_model.trainable = False  # Train head first then backbone
    x = base_model(x, training=False)
    x = layers.Dropout(0.4)(x)
    outputs = layers.Dense(
        num_classes,
        activation='softmax',
        kernel_regularizer=tf.keras.regularizers.l2(0.001)
    )(x)
    model = models.Model(inputs, outputs)
    return model, base_model


def finetune_backbone(model, base_model, n_layers=20):
    """
    Unfreezes the top N layers of the backbone for fine-tuning.
    Parameters:
    ----------
    model : tf.keras.Model
        The full model including the backbone and classification head
    base_model : tf.keras.Model
        The backbone model (EfficientNet-B0 without head) to unfreeze layers in
    n_layers : int
        Number of top layers in the backbone to unfreeze for fine-tuning
    Returns:
    ---------
    model : tf.keras.Model
        The model with the specified layers of the backbone unfrozen for training
    """
    base_model.trainable = True  # Train n_layers of backbone after head
    for layer in base_model.layers[:-n_layers]:  # Modify the parent through the child layers
        layer.trainable = False
    return model


def resize_dataset(images, target_size=(384, 384), batch_size=64):
    """Resize image tensors to a fixed spatial size for EfficientNet training.
    
    Processes in batches to avoid allocating the full dataset in memory at once.
    """
    if images.ndim == 3:
        images = images[..., np.newaxis]
    n = images.shape[0]
    h, w = target_size
    out = np.empty((n, h, w, images.shape[-1]), dtype=np.float32)
    for start in range(0, n, batch_size):
        end = min(start + batch_size, n)
        batch = tf.image.resize(images[start:end], target_size, method='bilinear')
        out[start:end] = batch.numpy()
    return out


# Reduce learning rate if val loss plateaus
lr_scheduler = ReduceLROnPlateau(
    monitor='val_loss',
    factor=0.5,
    patience=2,
    min_lr=1e-7,
    verbose=1
)


if __name__ == "__main__":
    """
    Code Starts Here
    """
    img_size = 1200
    path = 'sandbox\\classification\\training\\numpy\\'

    training_set = np.load(os.path.join(path, 'X_train.npy'))  # Data is X
    training_labels = np.load(os.path.join(path, 'Y_train.npy'))  # Labels are Y

    # Model needs int labels, convert from string: surf=0, transient=1, thunder=2
    label_map = {'surf': 0, 'transient': 1, 'thunder': 2}
    Y_train = np.array([label_map[l] for l in training_labels], dtype=np.int32)
    X_train = training_set.astype(np.float32)

    test_set = np.load(os.path.join(path, 'X_test.npy'))
    test_label = np.load(os.path.join(path, 'Y_test.npy'))
    X_test = test_set.astype(np.float32)
    Y_test = np.array([label_map[l] for l in test_label], dtype=np.int32)

    val_set = np.load(os.path.join(path, 'X_val.npy'))
    val_label = np.load(os.path.join(path, 'Y_val.npy'))
    X_val = val_set.astype(np.float32)
    Y_val = np.array([label_map[l] for l in val_label], dtype=np.int32)
    # Resize all splits to a manageable EfficientNet input size.
    target_size = (384, 384)
    X_train = resize_dataset(X_train, target_size=target_size)
    X_val = resize_dataset(X_val, target_size=target_size)
    X_test = resize_dataset(X_test, target_size=target_size)

    print(f"Train: {X_train.shape[0]}, Val: {X_val.shape[0]}, Test: {X_test.shape[0]}")
    print(f"Resized input shape: {X_train.shape[1:]}")

    # Build and compile the model 
    model, base_model = build_efficientnetb0(input_shape=X_train.shape[1:], num_classes=3)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.0001),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    # Checkpoints and callbacks
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        )
    ]
    reduce_lr = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=0.5, patience=3, min_lr=1e-7
    )
    checkpoint = tf.keras.callbacks.ModelCheckpoint(
        'best_efficientnet.keras',
        monitor='val_accuracy',
        save_best_only=True,
        mode='max'
    )
    # Balance initial class weights based on distribution in training set
    CLASS_NAMES = ['Surf(0)', 'Transient(1)', 'Thunder(2)']
    unique, counts = np.unique(Y_train, return_counts=True)
    print("\n=== CLASS BALANCE ===")
    print(f"Training set: {dict(zip([CLASS_NAMES[i] for i in unique], counts))}")

    unique_val, counts_val = np.unique(Y_val, return_counts=True)
    print(f"Validation set: {dict(zip([CLASS_NAMES[i] for i in unique_val], counts_val))}")

    unique_test, counts_test = np.unique(Y_test, return_counts=True)
    print(f"Test set: {dict(zip([CLASS_NAMES[i] for i in unique_test], counts_test))}")
    print("===================")
    print(f"Input min/max: {X_train.min():.4f} / {X_train.max():.4f}")

    total_samples = len(Y_train)
    n_class_0 = np.sum(Y_train == 0)  # Surf count
    n_class_1 = np.sum(Y_train == 1)  # Transient count
    n_class_2 = np.sum(Y_train == 2)  # Thunder count
    weight_0 = total_samples / (3.0 * n_class_0) if n_class_0 > 0 else 1.0
    weight_1 = total_samples / (3.0 * n_class_1) if n_class_1 > 0 else 1.0
    weight_2 = total_samples / (3.0 * n_class_2) if n_class_2 > 0 else 1.0

    weights_dict = {
        0: weight_0,  # Weight for Surf
        1: weight_1,  # Weight for Transient
        2: weight_2   # Weight for Thunder
    }
    print(f"Calculated class weights: {weights_dict}")

    print(Y_train.shape)
    print(type(Y_train))

    # Phase 1: Train classification head
    print("\n=== Phase 1: Training classification head ===")
    history = model.fit(
        X_train,
        Y_train,
        validation_data=(X_val, Y_val),
        epochs=12,
        batch_size=16,
        class_weight=weights_dict,
        callbacks=[reduce_lr, checkpoint] 
    )

    # Phase 2: Unfreeze top layers of backbone and fine-tune with lower LR
    print("\n=== Phase 2: Fine-tuning backbone ===")
    model = finetune_backbone(model, base_model, n_layers=20)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=2e-5),
        loss='sparse_categorical_crossentropy',
        metrics=['accuracy']
    )
    # Checkpoints and callbacks
    reduce_lr_ft = tf.keras.callbacks.ReduceLROnPlateau(
        monitor='val_loss', factor=0.5, patience=3, min_lr=1e-7
    )
    early_stop_ft = tf.keras.callbacks.EarlyStopping(
        monitor='val_loss', patience=5, restore_best_weights=True
    )
    checkpoint_ft = tf.keras.callbacks.ModelCheckpoint(
        'best_efficientnet.keras',
        monitor='val_accuracy',
        save_best_only=True,
        mode='max'
    )

    history_ft = model.fit(
        X_train,
        Y_train,
        validation_data=(X_val, Y_val),
        epochs=24,
        batch_size=16,
        class_weight=weights_dict,
        callbacks=[reduce_lr_ft, early_stop_ft, checkpoint_ft]
    )

    # Merge histories
    for key in history.history:
        history.history[key].extend(history_ft.history[key])

    model.load_weights('best_efficientnet.keras') 
    results = model.evaluate(X_test, Y_test)

    print(f"Final Test Accuracy: {results[1]}")

    # Print classification report and confusion matrix
    preds = model.predict(X_test)
    print(f"\nPrediction stats: min={preds.min():.4f}, max={preds.max():.4f}, mean={preds.mean():.4f}")
    print(f"Predictions shape: {preds.shape}")
    y_pred_class = np.argmax(preds, axis=1)
    y_true_class = Y_test.astype(int).flatten()
    pred_unique, pred_counts = np.unique(y_pred_class, return_counts=True)
    print(f"Prediction distribution: {dict(zip([CLASS_NAMES[i] for i in pred_unique], pred_counts))}")
    print(confusion_matrix(y_true_class, y_pred_class))
    print(classification_report(y_true_class, y_pred_class, target_names=['surf', 'transient', 'thunder']))
    plt.figure(figsize=(12, 5))

    # Plot model metrics
    plt.subplot(1, 2, 1)
    plt.plot(history.history['loss'], label='Training Loss')
    plt.plot(history.history['val_loss'], label='Validation Loss')
    plt.title('Model Loss')
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.legend()
    plt.grid(True)

    # --- PLOT ACCURACY ---
    plt.subplot(1, 2, 2)
    plt.plot(history.history['accuracy'], label='Training Accuracy')
    plt.plot(history.history['val_accuracy'], label='Validation Accuracy')
    plt.title('Model Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.grid(True)

    plt.show()
