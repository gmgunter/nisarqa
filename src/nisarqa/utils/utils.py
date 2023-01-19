from contextlib import contextmanager

import h5py
import nisarqa
import numpy as np

objects_to_skip = nisarqa.get_all(name=__name__)

@contextmanager
def open_h5_file(in_file, mode='r'):
    '''
    Open or create a handle for a h5 file.

    Parameters
    ----------
    in_file : str
        Filepath to an HDF5 file.
    mode : char
        The mode to open the input file.
        'r'         - Readonly, file must exist (default)
        'r+'        - Read/write, file must exist
        'w'         - Create file, truncate if exists
        'w-' or 'x' - Create file, fail if exists
        'a'         - Read/write if exists, create otherwise
    
    Returns
    -------
    handle : h5py.File
        Handle to `filepath` file
    '''
    try:
        input_file = h5py.File(in_file, mode)
    
    # TODO If file is already open, this error is thrown: BlockingIOError
    except (FileNotFoundError, IOError) as e:
        print('Could not open file. Add logger and remove this print statement.')
        # logger.log_message(logging_base.LogFilterError,
        #                     'File %s has a Fatal Error(s): %s' % (rslc_file, errors))
        raise
    else:
        yield input_file
    finally:
        input_file.close()


class DatasetNotFoundError(Exception):
    '''Custom exception name for when a dataset is
    not found in an e.g. HDF5 file.
    '''
    def __init__(self):
        super().__init__('Dataset not found.')


def compute_non_zero_mask(arr, epsilon=1.0E-05):
    '''
    Create a mask of the non-zero pixels in the input array.

    Elements in the input array that are approximately equal to zero, 
    based on the specified tolerance, are masked out.
    TODO - after development of the RSLC QA code is complete,
    check that this function is used. If not, delete.

    Parameters
    ----------
    arr : array_like
        The input array.
    epsilon : float, optional
        Absolute tolerance for determining if an element in `arr` 
        is nearly zero.

    Returns
    -------
    mask : Boolean array
        Array with same shape as `arr`.
        True for non-zero entries. False where the absolute 
        value of the entry is less than `epsilon`.
    '''
    zero_real = np.abs(arr) < epsilon
    return ~zero_real


def compute_mask_ok(arr, epsilon=1.0E-05):
    '''
    Create a mask of the valid (finite, non-zero) pixels in arr.

    TODO - after development of the RSLC QA code is complete,
    check that this function is used. If not, delete.

    Parameters
    ----------
    arr : array_like
        The input array
    epsilon : float, optional
        Tolerance for if an element in `arr` is considered 'zero'

    Returns
    -------
    mask_ok : array_like
        Array with same shape as `arr`.
        True for valid entries. Valid entries are finite values that are
        not approximately equal to zero.
        False for entries that have a nan or inf in either the real
        or imaginary component, or a zero in both real and imag components.

    See Also
    --------
    numpy.isfinite : Can be used to compute `finite_entries`
    utils.compute_non_zero_mask : Can be used to compute `non_zero`
    '''

    finite_mask = np.isfinite(arr)
    non_zero_mask = compute_non_zero_mask(arr, epsilon)
    mask_ok = finite_mask & non_zero_mask

    return mask_ok


def create_dataset_in_h5group(h5_file,
                              grp_path,
                              ds_name,
                              ds_data,
                              ds_description,
                              ds_units=None):
    '''
    Add a dataset with attributes to the provided group.

    Parameters
    ----------
    h5_file : h5py.File
        HDF5 File handle to save this dataset to
    grp_path : str
        Path to h5py Group to add the dataset and attributes to
    ds_name : str
        Name (key) for the Dataset in the `grp_path`
    ds_data : array_like or str
        Data to be stored as a Dataset in `grp_path`.
    ds_description : str
        Description of `ds_data`; will be stored in a `description`
        attribute for the new Dataset
    ds_units : str, optional
        Units of `ds_data`; will be stored in a `units` attribute
        for the new Dataset.
        For NISAR datasets, use this convention:
            - If the values have dimensions, use CF-compliant names (e.g. 'meters')
            - If the values are numeric but dimensionless (e.g. ratios),
              set `ds_units` to 'unitless'
            - If the values are inherently descriptive and have no units
              (e.g. a file name, or a list of frequency names such as ['A', 'B']),
              then set `ds_units` to None so that no units attribute
              is created.
        Defaults to None (no units attribute will be created)
    '''

    grp = h5_file.require_group(grp_path)

    ds = grp.create_dataset(ds_name, data=ds_data)

    if ds_units is not None:
        ds.attrs.create(name='units', data=ds_units,
                            dtype=f'<S{len(ds_units)}')

    ds.attrs.create(name='description', data=ds_description, 
                        dtype=f'<S{len(ds_description)}')


def multi_line_string_iter(multiline_str):
    '''
    Iterator for a multi-line string.
    
    Strips leading and trailing whitespace, and returns one line at a time.

    Parameters
    ----------
    multiline_str : str
        The string to be iterated over

    Yields
    ------
    line : str
        The next line in `multiline_str`, with the leading and trailing
        whitespace stripped.
    '''
    return iter([x.strip() for x in multiline_str.splitlines()])


def get_nested_element_in_dict(source_dict, path_to_element):
    '''
    Returns the value of the last key in the `path_to_element`.

    Parameters
    ----------
    source_dict : dict
        Nested dictionary to be parsed
    path_to_element : sequence
        Sequence which define a nested path in `source_dict` to
        the desired value.
    
    Returns
    -------
    element : Any
        The value of the final key in the `path_to_element` sequence

    Example
    -------
    >>> src = {'a' : 'dog', 'b' : {'cat':'lulu', 'toy':'mouse'}}
    >>> path = ['b']
    >>> get_nested_element_in_dict(src, path)
    {'cat': 'lulu', 'toy': 'mouse'}
    >>> path = ['b', 'toy']
    >>> get_nested_element_in_dict(src, path)
    'mouse'
    '''
    element = source_dict
    for nested_dict in path_to_element:
        element = element[nested_dict]
    return element


__all__ = nisarqa.get_all(__name__, objects_to_skip)
