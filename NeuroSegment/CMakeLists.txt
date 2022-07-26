#-----------------------------------------------------------------------------
set(MODULE_NAME NeuroSegment)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  )

set(MODULE_PYTHON_ICON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/Icons/${MODULE_NAME}.png
  )

set(MODULE_PYTHON_SEGMENTATIONS_RESOURCES
  Resources/Segmentations/DefaultSegmentation.seg.nrrd
  Resources/Segmentations/SegmentationCategoryTypeModifier-GeneralSegmentation.json
  )

set(MODULE_PYTHON_UI_RESOURCES
  Resources/UI/NeuroSegment.ui
  )

set(MODULE_PYTHON_RESOURCES
  ${MODULE_PYTHON_ICON_RESOURCES}
  ${MODULE_PYTHON_SEGMENTATIONS_RESOURCES}
  ${MODULE_PYTHON_UI_RESOURCES}
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

  # Additional build-time testing
  add_subdirectory(Testing)
endif()
