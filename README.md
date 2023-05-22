[![DOI](https://zenodo.org/badge/195091636.svg)](https://zenodo.org/badge/latestdoi/195091636)

# SlicerNeuroSegmentation: HOA 2.0 Neurosegmentation And Neuroparcellation

SlicerNeuroSegmentation is an extension for [3D Slicer](http://slicer.org) designed to provide access to tools for segmenting neurological structures.

## Modules

- ### NeuroSegment
  This module provides access to tools for editing MRI images. Segments that are created using the module are automatically populated with the structures that need to be segmented.
![Screenshot of NeuroSegmentation extension](https://github.com/HOA-2/SlicerNeuroSegmentation/blob/main/Images/Screenshots/Neurosegmentation_Screenshot.png)

- ### NeuroSegment Parcellation
  This module provides tools that facilitate the segmentation of structures in the cerebral cortex by defining planes and tracing along sulci that are represented 3D mesh imported from FreeSurfer.
![Screenshot of NeuroParcellation extension](Images/Screenshots/NeuroParcellation_1.png)

- ### Curve Comparison
  This module evaluates the curve surface pathfinding parameters to find the parameters that perform optimally compared to a ground truth curve.

## User guides

- ### Neurosegmentation
  The manual for performing segmentations with the Neurosegmentation module is located here:
  https://cma.mgh.harvard.edu/wp-content/uploads/2023/04/HOA-Subcortical-Brain-Structure-Segmentation-Manual.pdf

- ### Neuroparcellation
  Instructions on the workflow using the Neuroparcellation module can be found [here](https://cma.mgh.harvard.edu/research-2/).
  
  Additional information on the interface can be found [here](docs/NeuroParcellation.md).

## Support

If you encounter any issues or have any questions, feel free to submit an issue [here](https://github.com/PerkLab/SlicerNeuroSegmentation/issues/new).

## Citation

Rushmore R.J., Sunderland, K., Carrington H., Chen J., Halle M., Lasso A., Papadimitriou G., Prunier N., Rizzoni E., Vessey B., Wilson-Braun P., Rathi Y.,  Kubicki M., Bouix S., Yeterian E. and Makris N. (2022) Anatomically curated segmentation of human subcortical structures in high resolution magnetic resonance imaging: An open science approach. Front. Neuroanat. 16:894606. doi:10.3389/fnana.2022.894606

## Acknowledgements

Development of SlicerNeuroSegmentation was partially funded by Brigham and Women's Hospital through NIH grant R01MH112748
