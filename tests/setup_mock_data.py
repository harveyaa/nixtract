"""Functions to generate mock data files for tests"""
import os
import numpy as np
import nibabel as nib
import nibabel.cifti2 as ci

## Nifti

def atlas_to_func(img, out, n=10):
    """Create a mock functional (4D) data file

    The resulting 4th dimension will contain volumetric duplicates of the
    provided 3D image. This enables a way to verify that expected data is 
    correctly extracted (e.g., label 1 should extract a timeseries of all 1's, 
    etc).  

    Parameters
    ----------
    img : str
        File name of 3D label/atlas image
    out : str
        File name of output 4D image
    n : int, optional
        Number of timepoints to generate, by default 100
    """
    img = nib.load(img)
    out_img = nib.concat_images([img] * n)
    out_img.to_filename(out)
    return out


def atlas_to_mask(img, label, out):
    """Create a single-region mask

    Parameters
    ----------
    img : str
        File name of 3D label/atlas image
    label : int
        Numeric label for region of interest
    out : str
        File name of output binary mask image
    """
    img = nib.load(img)
    arr = img.load_fdata().copy()
    out_img = nib.Nifti1Image(np.where(arr == label, 1, 0), img.header)
    out_img.to_filename(out)
    return out

## Gifti

def make_binary_annot(annot_file, label, out):
    """Create a single-region annotation file

    Parameters
    ----------
    annot_file : str
        Freesurfer annotation file (.annot)
    label : int
        Numeric label for label of interest
    out : str
        File name of output .annot
    """
    annot = nib.freesurfer.read_annot(annot_file)
    mask = np.where(annot[0] == label, 1, 0)

    ctab = np.array([[25, 25, 25, 0], [255, 255, 255, 255]])
    names = ['background', 'mask']
    nib.freesurfer.write_annot(out, labels=mask, ctab=ctab, names=names)
    return out


def annot_to_func(annot_file, out, n=10):
    """Create a mock func.gii from an annotation file

    All timepoints (darrays) in .func.gii are duplicates of the annotation 
    array. This enables a way to verify that expected data is correctly 
    extracted (e.g., label 1 should extract a timeseries of all 1's, etc).  

    Parameters
    ----------
    annot_file : str
        Freesurfer annotation file (.annot)
    out : str
        File name of output .func.gii
    n : int, optional
        Number of timepoints to generate, by default 100
    """
    annot = nib.freesurfer.read_annot(annot_file)
    darrays = []
    for i in range(n):
        x = nib.gifti.GiftiDataArray(annot[0], 
                                     intent='NIFTI_INTENT_TIME_SERIES',
                                     datatype='NIFTI_TYPE_FLOAT32')
        darrays.append(x)
    img = nib.GiftiImage(darrays)
    img.to_filename(out)
    return out
 

def annot_to_gifti(annot_file, out):
    """Converts FreeSurfer-style annotation file `atlas` to a label.gii

    Based on Ross' code:
    https://github.com/rmarkello/abagen/blob/28e238cf6a12ecb3a8fde0abb70ab0b6e9108394/abagen/images.py#L53-L79

    Parameters
    ----------
    annot_file : os.PathLike
        Surface annotation file (.annot)
    out : str
        File name of output .label.gii

    """
    labels, ctab, names = nib.freesurfer.read_annot(annot_file)

    darr = nib.gifti.GiftiDataArray(labels, intent='NIFTI_INTENT_LABEL',
                                    datatype='NIFTI_TYPE_INT32')
    labeltable = nib.gifti.GiftiLabelTable()
    for key, label in enumerate(names):
        (r, g, b), a = (ctab[key, :3] / 255), (1.0 if key != 0 else 0.0)
        glabel = nib.gifti.GiftiLabel(key, r, g, b, a)
        glabel.label = label.decode()
        labeltable.labels.append(glabel)

    img = nib.GiftiImage(darrays=[darr], labeltable=labeltable)
    img.to_filename(out)
    return out

## CIFTI

def dlabel_to_dtseries(dlabel, out, n=10):
    """Create a mock .dtseries.nii from an .dlabel file

    All timepoints (rows) in .dtseries.nii are duplicates of the .dlabel array.
    This enables a way to verify that expected data is correctly extracted 
    (e.g., label 1 should extract a timeseries of all 1's, etc). 

    Parameters
    ----------
    dlabel : str
        File name of a .dlabel.nii file
    out : str
        File name of output .dtseries.nii
    n : int, optional
        Number of timepoints to generate, by default 100
    """

    dlabel = nib.load(dlabel)

    # imitate data with TR=2
    label_array = dlabel.get_fdata().ravel()
    tseries = np.tile(label_array, (n, 1))
    data_map = ci.Cifti2MatrixIndicesMap(
        applies_to_matrix_dimension=(0, ), 
        indices_map_to_data_type='CIFTI_INDEX_TYPE_SERIES',
        number_of_series_points=tseries.shape[0], 
        series_start=0, 
        series_step=2,
        series_exponent=0,
        series_unit='SECOND'
    )
    # take brain models from dlabel
    model_map = ci.Cifti2MatrixIndicesMap(
        applies_to_matrix_dimension=(1, ), 
        indices_map_to_data_type='CIFTI_INDEX_TYPE_BRAIN_MODELS',
        maps=list(dlabel.header.get_index_map(1).brain_models)
    )
    volume = dlabel.header.get_index_map(1).volume
    if volume is not None:
        model_map.volume = dlabel.header.get_index_map(1).volume

    # make header
    matrix = ci.Cifti2Matrix()
    matrix.append(data_map)
    matrix.append(model_map)
    hdr = ci.Cifti2Header(matrix)

    out_dtseries = ci.Cifti2Image(tseries, hdr) 
    out_dtseries.to_filename(out)
    return out


def dlabel_atlas_to_mask(dlabel, label, out):
    """Convert an atlas to a single region (i.e. binary) mask 

    Parameters
    ----------
    dlabel : str
        File name of a .dlabel.nii file
    label : int
        Numeric label for region of interest
    out : str
        File name of output .dlabel.nii
    """
    dlabel = nib.load(dlabel)
    arr = dlabel.get_fdata()
    mask = np.where(arr == label, label, 0)
    mask_img = ci.Cifti2Image(mask, header=dlabel.header)
    mask_img.to_filename(out)
    return out


def yeo_to_91k(dlabel, medial_wall, reference, out):
    """Convert Yeo-style dlabels (Yeo and Schaefer parcellations) to 91k 
    grayordinate space
    
    The Yeo lab generates dlabel's inclusive of medial wall vertices and only 
    for the cortical surfaces. This is different from how typical dlabels are 
    formatted, which exclude medial wall vertices and include voxels from all 
    subcortical and cerebellar structures (i.e. the full 91k grayordinate 
    space). This function corrects Yeo dlabels to proper 91k grayordinates.  

    Parameters
    ----------
    dlabel : str
        A Yeo-style .dlabel.nii atlas
    medial_wall : str
        HCP medial wall mask (.dlabel.nii)
    reference : str
        A reference .dlabel.nii file with 91k grayordinates and all brain 
        models included
    out : str
        Output 91k grayordinate .dlabel.nii file
    """
    dlabel = nib.load(dlabel)
    medial_wall = nib.load(medial_wall)
    ref = nib.load(reference)

    # remove medial wall vertices
    array = dlabel.get_fdata()
    corrected_array = array[np.logical_not(medial_wall.get_fdata())]

    # expand to 91k
    grayordinates = np.zeros(ref.shape)
    grayordinates[0, :corrected_array.shape[0]] = corrected_array
    
    # make header
    labels = dlabel.header.get_axis(index=0).label[0]
    label_table = ci.Cifti2LabelTable()
    for key, (tag, rgba) in labels.items():
        label_table[key] = ci.Cifti2Label(key, tag, *rgba)
    
    maps = [ci.Cifti2NamedMap('labels', ci.Cifti2MetaData({}), label_table)]
    label_map = ci.Cifti2MatrixIndicesMap(
        applies_to_matrix_dimension=(0, ), 
        indices_map_to_data_type='CIFTI_INDEX_TYPE_LABELS',
        maps=maps
    )
    model_map = ci.Cifti2MatrixIndicesMap(
        applies_to_matrix_dimension=(1, ), 
        indices_map_to_data_type='CIFTI_INDEX_TYPE_BRAIN_MODELS',
        maps=list(ref.header.get_index_map(1).brain_models)
    )
    model_map.volume = ref.header.get_index_map(1).volume

    matrix = ci.Cifti2Matrix()
    matrix.append(label_map)
    matrix.append(model_map)
    hdr = ci.Cifti2Header(matrix)

    out_dtseries = ci.Cifti2Image(grayordinates, hdr) 
    out_dtseries.to_filename(out)
    return out

def main():

    print('Setting up mock data...')
    os.makedirs('data/mock', exist_ok=True)

    ## NIfTIs


    ## GIfTIs


    ## CIfTIs
    schaef_cifti =  'data/Schaefer2018_100Parcels_7Networks_order.dlabel.nii'
    gordon_cifti = 'data/Gordon333_FreesurferSubcortical.32k_fs_LR.dlabel.nii'
    mwall = 'data/Human.MedialWall_Conte69.32k_fs_LR.dlabel.nii'
    
    schaef_91k = 'data/mock/schaefer_91k.dlabel.nii'
    schaef_91k = yeo_to_91k(schaef_cifti, mwall, gordon_cifti, schaef_91k)

    schaef_91k_dtseries = 'data/mock/schaefer_91k.dtseries.nii'
    dlabel_to_dtseries(schaef_91k, schaef_91k_dtseries)

    schaef_dtseries = 'data/mock/schaefer.dtseries.nii'
    dlabel_to_dtseries(schaef_cifti, schaef_dtseries)

    gordon_dtseries = 'data/mock/gordon.dtseries.nii'
    dlabel_to_dtseries(gordon_cifti, gordon_dtseries)

    schaefer_LH_Vis_4_mask = 'data/mock/schaefer_LH_Vis_4.dlabel.nii'
    dlabel_atlas_to_mask(schaef_cifti, 4, schaefer_LH_Vis_4_mask)

    gordon_L_SMhand_10_mask = 'data/mock/gordon_L_SMhand_10.dlabel.nii'
    dlabel_atlas_to_mask(gordon_cifti, 273, gordon_L_SMhand_10_mask)

if __name__ == '__main__':
    main()