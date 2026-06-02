import numpy as np
from scipy.signal import hilbert
import os
import numpy as np
import matplotlib.pyplot as plt
import obspy
from obspy.clients.fdsn import Client
import json
from obspy import Stream
from sklearn.model_selection import train_test_split
#from scipy.signal import cwt, ricker
from classify_event import single_stack


def create_train_stack(all_entries, fname, pname, inv, window=12.8, target_size=64, stack_size=1, overlap=0, freq_range=(0.8, 8.0), do_mvida=False, num_mvida=1, class_list=[]):
    """
    Takes a detection stream and generates a single CWT stack for classification.
    Parameters
    ----------
    all_entries : list of dicts
        List of detection entries, each containing metadata and class labels.
    fname : str
        Filename prefix for saving the generated numpy arrays.
    pname : str
        Path prefix for saving the generated numpy arrays.
    inv : obspy Inventory object
        Inventory containing station metadata for processing.
    window : float, optional
        Time window (in seconds) for the stack centered around the detection time. Default is 12.8 seconds.
    target_size : int, optional
        Desired size (in pixels) of the output CWT image (target_size x target_size). Default is 64.
    stack_size : int, optional
        Number of traces to stack together for each sample. Default is 1 (no stacking).
    overlap : float, optional
        Fractional overlap between stacked traces (0 to 1). Default is 0 (no overlap).
    freq_range : tuple, optional
        Frequency range (in Hz) for bandpass filtering the data before CWT. Default is (0.8, 8.0) Hz.
    do_mvida : bool, optional
        Whether to apply MVIDA augmentation for additional training samples. Default is False.
    num_mvida : int, optional
        Number of MVIDA-augmented versions to create per original sample (only used if do_mvida is True). Default is 1.
    class_list : list of str, optional
        List of class labels to consider for processing. Only entries with classes in this list will be processed. Default is an empty list (no classes).
    
    Returns
    -------
    rt : int
        Integer representing success (1) or failure (0) of the stack creation process.
    """
    rt = 0
    cl = Client("IRIS")
    X_data = []
    Y_labels = []
    if (class_list == []):
        print("No class list provided. Exiting...")
        return rt
    for num, entry in enumerate(all_entries):
        while True:
            print(f"Processed entry {entry['Class']} {num+1}/{len(all_entries)}.")
            try:
                buffer = 20.
                center_time = obspy.UTCDateTime(entry['Time (UTC)']+'Z')
                s_time = center_time - (window / 2) - buffer
                e_time = center_time + (window / 2) + buffer
                strm_g = cl.get_waveforms(network="IM", station="I59*", location="", channel="BDF", starttime=s_time, endtime=e_time)
                num_versions = num_mvida[class_list.index(entry['Class'])] if do_mvida else 1
                for v in range(num_versions):
                    # v == 0 always uses the clean weighted stack; subsequent versions use MVIDA augmentation
                    use_mvida = do_mvida and v > 0
                    sample = single_stack(
                        strm_g.copy(), inv, freq_range, center_time,
                        window, stack_size, overlap,
                        entry['Back Azimuth'], entry['Trace Vel. (m/s)'],
                        target_size, do_mvida=use_mvida
                    )
                    X_data.append(sample)
                    Y_labels.append(entry['Class'])

                print(f"Dataset size: {len(X_data)}")
                break
            except Exception as e:
                print(f"Error processing entry {num+1}: {e}. Retrying...")
                continue

    X_train = np.array(X_data)  # Shape: (samples, height, width, channels)
    Y_train = np.array(Y_labels)
    print(f"Sample shape: {X_train[0].shape}")
    print(f"First label: {Y_train[0]}")

    np.save(os.path.join(pname, f'X_{fname}.npy'), X_train)
    np.save(os.path.join(pname, f'Y_{fname}.npy'), Y_train)

    print("Serialization Complete.")
    print(f"Final X Data Shape: {X_train.shape}")
    print(f"Final Y Data Shape: {Y_train.shape}")
    rt = 1
    return rt


if __name__ == "__main__":
    path = os.getcwd() + '/sandbox/identification/'
    rel_path = os.path.join(path, 'training', 'numpy')
    cl = Client("IRIS")
    with open(path+'training/json/merged_detections.json', 'r') as f:
        detections = json.load(f)
    inv = obspy.read_inventory(path+'training/I59US_station.xml')
    all_entries = detections
    np.random.shuffle(all_entries)
    labels_for_splitting = [x['Class'] for x in all_entries]
    # Split data into train, test, val sets (70%, 15%, 15%)
    train_entries, testval_entries = train_test_split(
        all_entries,
        test_size=0.3,          
        random_state=42,
        shuffle=True,
        stratify=labels_for_splitting 
    )
    labels_testval = [x['Class'] for x in testval_entries]
    test_entries, val_entries = train_test_split(
        testval_entries,
        test_size=0.5,
        random_state=42,
        shuffle=True,
        stratify=labels_testval
    )

    create_train_stack(train_entries, 'train', rel_path, inv, window=38.4, target_size=384, stack_size=1, overlap=0, freq_range=(0.8, 8.0), do_mvida=True, num_mvida=[10, 12, 12, 20], class_list=['surf', 'transient', 'thunder', 'artillery'])
    create_train_stack(test_entries, 'test', rel_path, inv, window=38.4, target_size=384, stack_size=1, overlap=0, freq_range=(0.8, 8.0), do_mvida=False, num_mvida=[10, 12, 12, 20], class_list=['surf', 'transient', 'thunder', 'artillery'])
    create_train_stack(val_entries, 'val', rel_path, inv, window=38.4, target_size=384, stack_size=1, overlap=0, freq_range=(0.8, 8.0), do_mvida=False, num_mvida=[10, 12, 12, 20], class_list=['surf', 'transient', 'thunder', 'artillery'])