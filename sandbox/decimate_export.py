"""
Quick and simple functions to decimate and export data from an obspy stream

"""
import os

from obspy import Stream, UTCDateTime


def decimate_stream(strm: Stream, factor: int) -> Stream:
    """
    Decimate the stream by a given factor

    :param strm: The input stream to decimate
    :param factor: The decimation factor

    :return: The decimated stream
    """
    decimated_strm = strm.copy()
    try:
        if factor > 1:
            decimated_strm.decimate(factor, strict_length=False)
            
    except Exception as e:
        print(f"Error applying decimation: {e}")

    return decimated_strm


def export_mseed(strm: Stream, start_utc: UTCDateTime, end_utc: UTCDateTime, out_dir: str = ".") -> str:
    """
    Export each trace in the stream to a MiniSEED formatted file in the specified output directory
    (defaults to current working directory)

    :param strm: The stream to export
    :param start_utc: The start time of the data to export
    :param end_utc: The end time of the data to export
    :param out_dir: The directory to save the exported files (default is current directory)

    :return: A message indicating the export status
    """
    print(f"Exporting {len(strm)} traces to {out_dir} from {start_utc} to {end_utc}...")
    try:
        # Generate timestamp strings for filenames
        start_str = start_utc.strftime("%Y%m%d_%H%M%S")
        end_str = end_utc.strftime("%Y%m%d_%H%M%S")
        for tr in strm:
            file_name = f"{tr.stats.network}.{tr.stats.station}.{tr.stats.location}.{tr.stats.channel}"\
                        f"_{start_str}_to_{end_str}_view.mseed"
                    
            # Create a copy and slice it
            trace_copy = tr.copy()
            sliced_trace = trace_copy.slice(start_utc, end_utc)
                
            # Only add non-empty traces
            if len(sliced_trace.data) > 0:
                out_path = os.path.join(out_dir, file_name)
                sliced_trace.write(out_path, format="MSEED")
                print(f"Exported {file_name} successfully.")

    except Exception as e:
        return f"Error during export: {e}"
    
    return(f"Exported {len(strm)} traces to {out_dir} successfully.")


def decimate_and_export(strm: Stream, factor: int,
                        start_utc: UTCDateTime, end_utc: UTCDateTime, out_dir: str = ".") -> str:
    """
    Decimate the stream by a given factor and export to MiniSEED format

    :param strm: The input stream to decimate and export
    :param factor: The decimation factor
    :param start_utc: The start time of the data to export
    :param end_utc: The end time of the data to export
    :param out_dir: The directory to save the exported files (default is current directory)

    :return: A message indicating the export status
    """
    decimated_strm = decimate_stream(strm, factor)
    return export_mseed(decimated_strm, start_utc, end_utc, out_dir)
