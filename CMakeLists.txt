cmake_minimum_required(VERSION 3.13.4)

project(SlicerNeuroSegmentation)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/wiki/Documentation/Nightly/Extensions/NeuroSegmentation")
set(EXTENSION_CATEGORY "Neuroimaging")
set(EXTENSION_CONTRIBUTORS "Kyle Sunderland (Perk Lab (Queen's University))")
set(EXTENSION_DESCRIPTION "Extension for performing segmentation of FreeSurfer images and surfaces in Slicer.")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/NeuroSegmentation.png")
set(EXTENSION_SCREENSHOTURLS "")
set(EXTENSION_DEPENDS "SlicerFreeSurfer")

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

find_package(SlicerFreeSurfer REQUIRED)

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(NeuroSegment)
add_subdirectory(NeuroSegmentParcellation)
add_subdirectory(SurfaceAverage)
add_subdirectory(CurveComparison)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
